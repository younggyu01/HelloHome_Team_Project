# ==============================================================================
# correlation_view.py - 상관관계 분석 탭 (개선된 버전)
# ==============================================================================
# 이 파일은 동물의 다양한 특성(나이, 성별, 중성화, 색상 등)이 입양 성공 여부에
# 어떤 영향을 미치는지 심층적으로 분석하는 화면을 제공합니다.
#
# [개선된 분석 내용]
# 1. **입양 영향 요인 분석:** 나이, 중성화 여부, 색상 등 주요 요인들이
#    입양률에 미치는 영향을 명확하게 시각화합니다.
# 2. **종합적 관계 분석:** 여러 변수 간의 복합적인 관계를 한눈에 파악할 수 있는
#    고급 시각화(버블차트, 페어플롯)를 제공합니다.
# ==============================================================================

import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime

def preprocess_for_correlation(final_animals):
    """상관관계 분석에 필요한 데이터 전처리를 수행하는 함수"""
    df = final_animals.copy()

    # --- 공통 전처리 ---
    df['notice_date'] = pd.to_datetime(df['notice_date'], errors='coerce')
    df.dropna(subset=['notice_date'], inplace=True)

    # 1. 입양 성공 여부 (binary)
    df['is_adopted'] = (df['process_state'] == '종료(입양)').astype(int)

    # 2. 나이(age) 숫자형으로 변환
    df['age_str'] = df['age'].astype(str)
    df['birth_year'] = pd.to_numeric(df['age_str'].str.extract(r'(\d{4})')[0], errors='coerce')
    current_year = datetime.now().year
    df['age_numeric'] = current_year - df['birth_year']
    df.loc[df['age_numeric'] > 80, 'age_numeric'] = np.nan

    # 3. 중성화 여부 (neuter) binary
    df['is_neutered'] = (df['neuter'] == 'Y').astype(int)

    # 4. 색상 데이터 정제 (주요 색상 추출)
    if 'color' in df.columns:
        df['color_group'] = df['color'].str.extract(r'(흰|검|갈|노랑|회|크림|삼색|치즈|고등어|블랙탄)')[0]
        df['color_group'] = df['color_group'].replace({'노랑': '치즈/노랑', '치즈': '치즈/노랑', '검': '검정/블랙탄', '블랙탄': '검정/블랙탄'})
        df['color_group'].fillna('기타', inplace=True)
    else:
        df['color_group'] = '정보 없음'
        
    return df

def show(final_animals, filtered_shelters):
    """
    '상관관계 분석' 탭의 전체 UI를 그리고 로직을 처리하는 메인 함수입니다.
    """
    st.subheader("🔍 입양 영향 요인 분석")
    st.info("동물의 여러 특성들이 입양 성공에 어떤 영향을 미치는지 다각도로 분석합니다.")

    if final_animals.empty:
        st.warning("분석할 데이터가 부족합니다. 필터 조건을 변경해보세요.")
        return

    try:
        df = preprocess_for_correlation(final_animals)
    except Exception as e:
        st.error(f"데이터 전처리 중 오류가 발생했습니다: {e}")
        return

    # ==========================================================================
    # 1. 주요 입양 영향 요인 분석
    # ==========================================================================
    st.markdown("### Ⅰ. 주요 입양 영향 요인 분석")

    # --- 나이 vs 입양 여부 (개선된 분석) ---
    st.markdown("#### 1. 나이에 따른 입양률 변화")
    if df['age_numeric'].notna().any():
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**입양 성공/실패 그룹의 나이 분포**")
            fig_age_box = px.box(df, x='is_adopted', y='age_numeric', 
                                   color='is_adopted', template='plotly_white',
                                   labels={'is_adopted': '입양 여부 (1:성공, 0:실패)', 'age_numeric': '나이'},
                                   color_discrete_map={0: 'lightcoral', 1: 'lightgreen'})
            fig_age_box.update_layout(margin=dict(t=30, b=10))
            st.plotly_chart(fig_age_box, use_container_width=True)
        
        with col2:
            st.markdown("**나이대별 입양률**")
            bins = [0, 1, 3, 8, df['age_numeric'].max() + 1]
            labels = ['1살 미만', '1-3살', '4-7살', '8살 이상']
            df['age_group'] = pd.cut(df['age_numeric'], bins=bins, labels=labels, right=False)
            age_adoption_rate = df.groupby('age_group')['is_adopted'].mean().reset_index()
            age_adoption_rate['adoption_rate_pct'] = (age_adoption_rate['is_adopted'] * 100).round(1)

            fig_age_bar = px.bar(age_adoption_rate, x='age_group', y='adoption_rate_pct', 
                                 text='adoption_rate_pct', template='plotly_white',
                                 labels={'age_group': '나이대', 'adoption_rate_pct': '입양률 (%)'})
            fig_age_bar.update_traces(texttemplate='%{text}%', textposition='outside')
            fig_age_bar.update_layout(margin=dict(t=30, b=10))
            st.plotly_chart(fig_age_bar, use_container_width=True)
    else:
        st.info("나이 데이터가 부족하여 분석할 수 없습니다.")

    # --- 중성화 여부 vs 입양률 ---
    st.markdown("#### 2. 중성화 여부에 따른 입양률")
    neutered_adoption_rate = df.groupby('is_neutered')['is_adopted'].mean().reset_index()
    neutered_adoption_rate['is_neutered'] = neutered_adoption_rate['is_neutered'].map({0: '중성화 X', 1: '중성화 O'})
    neutered_adoption_rate['adoption_rate_pct'] = (neutered_adoption_rate['is_adopted'] * 100).round(1)

    fig_neuter_bar = px.bar(neutered_adoption_rate, x='is_neutered', y='adoption_rate_pct', 
                            color='is_neutered', text='adoption_rate_pct', template='plotly_white',
                            labels={'is_neutered': '중성화 여부', 'adoption_rate_pct': '입양률 (%)'})
    fig_neuter_bar.update_traces(texttemplate='%{text}%', textposition='outside')
    fig_neuter_bar.update_layout(showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig_neuter_bar, use_container_width=True)

    # --- 색상 vs 입양률 ---
    st.markdown("#### 3. 색상에 따른 입양률")
    if 'color_group' in df.columns and df['color_group'].nunique() > 1:
        color_adoption_rate = df.groupby('color_group')['is_adopted'].mean().reset_index()
        color_adoption_rate['adoption_rate_pct'] = (color_adoption_rate['is_adopted'] * 100).round(1)
        color_adoption_rate = color_adoption_rate.sort_values('adoption_rate_pct', ascending=False)

        fig_color_bar = px.bar(color_adoption_rate, x='color_group', y='adoption_rate_pct', 
                               color='color_group', text='adoption_rate_pct', template='plotly_white',
                               labels={'color_group': '색상 계열', 'adoption_rate_pct': '입양률 (%)'})
        fig_color_bar.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_color_bar.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig_color_bar, use_container_width=True)
    else:
        st.info("색상 데이터가 부족하여 분석할 수 없습니다.")

    # ==========================================================================
    # 2. 종합적 관계 분석
    # ==========================================================================
    st.markdown("---")
    st.markdown("### Ⅱ. 종합적 관계 분석")

    # --- 품종별 보호기간 vs 입양률 (Bubble Chart) ---
    st.markdown("#### 4. 품종별 보호 기간과 입양률의 관계")
    if 'kind_name' in df.columns:
        df['protection_duration'] = (datetime.now() - df['notice_date']).dt.days
        kind_stats = df.groupby('kind_name').agg(
            avg_duration=('protection_duration', 'mean'),
            adoption_rate=('is_adopted', 'mean'),
            count=('desertion_no', 'size')
        ).reset_index()
        
        top_30_kinds = kind_stats[kind_stats['count'] > 10].nlargest(30, 'count')

        if not top_30_kinds.empty:
            top_30_kinds['adoption_rate_pct'] = (top_30_kinds['adoption_rate'] * 100).round(1)
            fig_bubble = px.scatter(top_30_kinds, x='avg_duration', y='adoption_rate_pct', size='count', color='kind_name', 
                                    hover_name='kind_name', size_max=60, template='plotly_white',
                                    labels={'avg_duration': '평균 보호 기간 (일)', 'adoption_rate_pct': '입양률 (%)', 'count': '보호 동물 수'})
            fig_bubble.update_layout(showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig_bubble, use_container_width=True)
        else:
            st.info("분석에 충분한 품종 데이터가 없습니다.")
    else:
        st.info("품종 데이터가 없습니다.")

    # --- 다변량 상관관계 (Pair Plot) ---
    st.markdown("#### 5. 주요 변수 간 종합 분석 (Pair Plot)")
    with st.expander("자세히 보기", expanded=False):
        st.markdown("동물의 주요 숫자 특성(나이, 보호기간, 성별, 중성화여부, 입양여부)들 간의 관계를 한 번에 보여줍니다. 대각선은 각 변수의 분포를, 나머지는 변수 쌍의 관계를 나타냅니다.")

    df['sex_numeric'] = (df['sex'] == 'M').astype(int)
    pairplot_df = df[['age_numeric', 'protection_duration', 'sex_numeric', 'is_neutered', 'is_adopted']].dropna()
    if not pairplot_df.empty:
        fig_pairplot = px.scatter_matrix(pairplot_df, 
                                         dimensions=['age_numeric', 'protection_duration', 'sex_numeric', 'is_neutered'],
                                         color='is_adopted', 
                                         color_continuous_scale='RdBu_r',
                                         labels={'age_numeric':'나이', 'protection_duration':'보호기간', 'sex_numeric':'성별(1=M)', 'is_neutered':'중성화(1=Y)', 'is_adopted':'입양여부'})
        fig_pairplot.update_layout(height=700, margin=dict(t=50, b=10))
        st.plotly_chart(fig_pairplot, use_container_width=True)
    else:
        st.info("종합 분석을 위한 데이터가 부족합니다.")