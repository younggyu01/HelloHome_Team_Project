import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import numpy as np

# --- 데이터 전처리 ---
def preprocess_for_dashboard(final_animals: pd.DataFrame) -> pd.DataFrame:
    df = final_animals.copy()
    df['notice_date'] = pd.to_datetime(df['notice_date'], errors='coerce')
    df.dropna(subset=['notice_date'], inplace=True)

    df['age_str'] = df['age'].astype(str)
    df['birth_year'] = pd.to_numeric(df['age_str'].str.extract(r'(\d{4})')[0], errors='coerce')
    current_year = datetime.now().year
    df['age_numeric'] = current_year - df['birth_year']
    df.loc[df['age_numeric'] > 80, 'age_numeric'] = np.nan

    df['is_adopted'] = (df['process_state'] == '종료(입양)').astype(int)
    df['is_neutered'] = (df['neuter'] == 'Y').astype(int)

    if 'color' in df.columns:
        df['color_group'] = df['color'].str.extract(r'(흰|검|갈|노랑|회|크림|삼색|치즈|고등어|블랙탄)')[0]
        df['color_group'] = df['color_group'].replace({'노랑': '치즈/노랑', '치즈': '치즈/노랑', '검': '검정/블랙탄', '블랙탄': '검정/블랙탄'})
        df['color_group'].fillna('기타', inplace=True)
    else:
        df['color_group'] = '정보 없음'
        
    return df

# --- 차트 생성 함수들 ---
def plot_species_distribution(df: pd.DataFrame):
    st.markdown("#### 1. 축종별 보호 동물 비율")
    species_chart_data = df.groupby("upkind_name").size().reset_index(name='count')
    fig = px.pie(species_chart_data, names="upkind_name", values="count", hole=0.4,
                 color="upkind_name", color_discrete_map={'개': '#FFA07A', '고양이': '#87CEFA', '기타': '#90EE90'})
    fig.update_traces(textinfo='percent+label', pull=[0.05, 0.05, 0.05])
    fig.update_layout(showlegend=True, margin=dict(t=10, b=10), legend_title_text='축종')
    st.plotly_chart(fig, use_container_width=True)

def plot_age_distribution(df: pd.DataFrame):
    st.markdown("#### 2. 나이대별 보호 현황 및 입양률")
    if df['age_numeric'].notna().any():
        bins = [0, 1, 3, 8, df['age_numeric'].max() + 1]
        labels = ['1살 미만', '1-3살', '4-7살', '8살 이상']
        df['age_group'] = pd.cut(df['age_numeric'], bins=bins, labels=labels, right=False)
        age_group_stats = df.groupby('age_group').agg(total_count=('desertion_no', 'size'), adopted_count=('is_adopted', 'sum')).reset_index()
        age_group_stats['adoption_rate'] = (age_group_stats['adopted_count'] / age_group_stats['total_count'] * 100).round(1)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=age_group_stats['age_group'], y=age_group_stats['total_count'], name='보호 수', marker_color='lightblue'), secondary_y=False)
        fig.add_trace(go.Scatter(x=age_group_stats['age_group'], y=age_group_stats['adoption_rate'], name='입양률', marker_color='crimson'), secondary_y=True)
        fig.update_layout(title_text="나이대별 보호 수 및 입양률", template='plotly_white', margin=dict(t=50, b=10))
        fig.update_yaxes(title_text="보호 수 (마리)", secondary_y=False)
        fig.update_yaxes(title_text="입양률 (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("나이 데이터가 부족하여 분석할 수 없습니다.")

def plot_kind_distribution(df: pd.DataFrame):
    st.markdown("#### 3. 품종별 보호 현황 Top 10")
    if 'kind_name' in df.columns and not df['kind_name'].empty:
        top_10_kinds = df['kind_name'].value_counts().nlargest(10).index
        df_top_10 = df[df['kind_name'].isin(top_10_kinds)]
        kind_stats = df_top_10.groupby('kind_name').agg(total_count=('desertion_no', 'size'), adopted_count=('is_adopted', 'sum')).reset_index()
        kind_stats['adoption_rate'] = (kind_stats['adopted_count'] / kind_stats['total_count'] * 100).round(1)
        kind_stats = kind_stats.sort_values('total_count', ascending=False)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=kind_stats['kind_name'], y=kind_stats['total_count'], name='보호 수', marker_color='lightgreen'), secondary_y=False)
        fig.add_trace(go.Scatter(x=kind_stats['kind_name'], y=kind_stats['adoption_rate'], name='입양률', marker_color='purple'), secondary_y=True)
        fig.update_layout(title_text="상위 10개 품종의 보호 수 및 입양률", template='plotly_white', margin=dict(t=50, b=10))
        fig.update_yaxes(title_text="보호 수 (마리)", secondary_y=False)
        fig.update_yaxes(title_text="입양률 (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("세부 품종 데이터가 없습니다.")

def plot_adoption_trend(df: pd.DataFrame):
    st.markdown("#### 4. 월별 입양률 추이")
    if 'notice_date' in df.columns and not df['notice_date'].empty:
        adoption_df = df.copy()
        adoption_df['month'] = adoption_df['notice_date'].dt.to_period('M').dt.to_timestamp()
        monthly_stats = adoption_df.groupby('month').agg(total=('desertion_no', 'size'), adopted=('is_adopted', 'sum')).reset_index()
        monthly_stats['adoption_rate'] = monthly_stats.apply(lambda row: (row['adopted'] / row['total'] * 100) if row['total'] > 0 else 0, axis=1)
        fig = px.line(monthly_stats, x='month', y='adoption_rate', markers=True, template='plotly_white', labels={'month': '월', 'adoption_rate': '입양률 (%)'})
        fig.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("공고일 데이터가 없어 입양률 추이를 표시할 수 없습니다.")

def plot_regional_heatmap(df: pd.DataFrame, filtered_shelters: pd.DataFrame):
    st.markdown("#### 5. 지역별 월별 발생 건수 (상위 10개 지역)")
    if not filtered_shelters.empty:
        merged_data = pd.merge(df, filtered_shelters, on='shelter_name', how='left')
        if 'region' in merged_data.columns and not merged_data['region'].empty:
            top_regions = merged_data['region'].value_counts().nlargest(10).index
            df_top_regions = merged_data[merged_data['region'].isin(top_regions)].copy()
            df_top_regions['month'] = df_top_regions['notice_date'].dt.month
            available_months = sorted(df_top_regions['month'].unique())
            region_month_counts = df_top_regions.groupby(['region', 'month']).size().unstack(fill_value=0).reindex(columns=available_months, fill_value=0)
            if not region_month_counts.empty:
                fig = px.imshow(region_month_counts, labels=dict(x="월", y="지역명", color="발생 건수"), x=[f'{i}월' for i in available_months], y=region_month_counts.index, text_auto=True, aspect="auto", color_continuous_scale='YlGnBu')
                fig.update_layout(title_text='월별 유기동물 발생 건수 히트맵', title_x=0.5, margin=dict(t=80, b=10), xaxis=dict(side='top', title=None))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("히트맵을 그릴 데이터가 충분하지 않습니다.")
        else:
            st.info("지역(region) 데이터가 없어 히트맵을 표시할 수 없습니다.")
    else:
        st.info("보호소 데이터가 부족하여 지역별 분석을 수행할 수 없습니다.")

def plot_age_adoption_correlation(df: pd.DataFrame):
    st.markdown("#### 1. 나이에 따른 입양률 변화")
    if df['age_numeric'].notna().any():
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**입양 성공/실패 그룹의 나이 분포**")
            fig_age_box = px.box(df, x='is_adopted', y='age_numeric', color='is_adopted', template='plotly_white', labels={'is_adopted': '입양 여부 (1:성공, 0:실패)', 'age_numeric': '나이'}, color_discrete_map={0: 'lightcoral', 1: 'lightgreen'})
            fig_age_box.update_layout(margin=dict(t=30, b=10))
            st.plotly_chart(fig_age_box, use_container_width=True)
        with col2:
            st.markdown("**나이대별 입양률**")
            if 'age_group' not in df.columns:
                bins = [0, 1, 3, 8, df['age_numeric'].max() + 1]
                labels = ['1살 미만', '1-3살', '4-7살', '8살 이상']
                df['age_group'] = pd.cut(df['age_numeric'], bins=bins, labels=labels, right=False)
            age_adoption_rate = df.groupby('age_group')['is_adopted'].mean().reset_index()
            age_adoption_rate['adoption_rate_pct'] = (age_adoption_rate['is_adopted'] * 100).round(1)
            fig_age_bar = px.bar(age_adoption_rate, x='age_group', y='adoption_rate_pct', text='adoption_rate_pct', template='plotly_white', labels={'age_group': '나이대', 'adoption_rate_pct': '입양률 (%)'})
            fig_age_bar.update_traces(texttemplate='%{text}%', textposition='outside')
            fig_age_bar.update_layout(margin=dict(t=30, b=10))
            st.plotly_chart(fig_age_bar, use_container_width=True)
    else:
        st.info("나이 데이터가 부족하여 분석할 수 없습니다.")

def plot_neutering_adoption_rate(df: pd.DataFrame):
    st.markdown("#### 2. 중성화 여부에 따른 입양률")
    neutered_adoption_rate = df.groupby('is_neutered')['is_adopted'].mean().reset_index()
    neutered_adoption_rate['is_neutered'] = neutered_adoption_rate['is_neutered'].map({0: '중성화 X', 1: '중성화 O'})
    neutered_adoption_rate['adoption_rate_pct'] = (neutered_adoption_rate['is_adopted'] * 100).round(1)
    fig = px.bar(neutered_adoption_rate, x='is_neutered', y='adoption_rate_pct', color='is_neutered', text='adoption_rate_pct', template='plotly_white', labels={'is_neutered': '중성화 여부', 'adoption_rate_pct': '입양률 (%)'})
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

def plot_color_adoption_rate(df: pd.DataFrame):
    st.markdown("#### 3. 색상에 따른 입양률")
    if 'color_group' in df.columns and df['color_group'].nunique() > 1:
        color_adoption_rate = df.groupby('color_group')['is_adopted'].mean().reset_index()
        color_adoption_rate['adoption_rate_pct'] = (color_adoption_rate['is_adopted'] * 100).round(1)
        color_adoption_rate['color_group'] = color_adoption_rate['color_group'].apply(lambda x: x if '색' in x else f"{x}색")
        color_adoption_rate = color_adoption_rate.sort_values('adoption_rate_pct', ascending=False)
        fig = px.bar(color_adoption_rate, x='color_group', y='adoption_rate_pct', color='color_group', text='adoption_rate_pct', template='plotly_white', labels={'color_group': '색상 계열', 'adoption_rate_pct': '입양률 (%)'})
        fig.update_traces(texttemplate='%{text}%', textposition='outside')
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("색상 데이터가 부족하여 분석할 수 없습니다.")

# --- 탭 렌더링 함수 ---
def render_main_stats_tab(df: pd.DataFrame, filtered_shelters: pd.DataFrame):
    st.markdown("### Ⅰ. 핵심 통계 요약")
    plot_species_distribution(df)
    plot_age_distribution(df)
    plot_kind_distribution(df)

    st.markdown("---")
    st.markdown("### Ⅱ. 시간 및 지역별 심층 분석")
    plot_adoption_trend(df)
    plot_regional_heatmap(df, filtered_shelters)

def render_adoption_factors_tab(df: pd.DataFrame):
    st.markdown("### Ⅲ. 입양 영향 요인 분석")
    plot_age_adoption_correlation(df)
    plot_neutering_adoption_rate(df)
    plot_color_adoption_rate(df)

# --- 메인 함수 ---
def show(final_animals: pd.DataFrame, filtered_shelters: pd.DataFrame):
    st.subheader("📊 분석 대시보드")
    st.info("유기동물 데이터의 주요 현황, 시계열/지역별 패턴, 입양 영향 요인을 종합적으로 분석합니다.")

    if final_animals.empty:
        st.warning("분석할 데이터가 부족합니다. 필터 조건을 변경해보세요.")
        return

    try:
        df = preprocess_for_dashboard(final_animals)
    except Exception as e:
        st.error(f"데이터 전처리 중 오류가 발생했습니다: {e}")
        return

    tab1, tab2 = st.tabs(["📈 핵심 통계 및 시계열/지역별 분석", "🔍 입양 영향 요인 분석"])

    with tab1:
        render_main_stats_tab(df, filtered_shelters)

    with tab2:
        render_adoption_factors_tab(df)