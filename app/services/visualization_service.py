import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from datetime import datetime
import streamlit as st

# Корпоративные цвета Альфа Банка
ALFA_RED = "#EF3124"
ALFA_BLACK = "#333333"
ALFA_GRAY = "#F5F5F5"
ALFA_LIGHT_GRAY = "#E5E5E5"

# Цветовая палитра для графиков
ALFA_COLOR_SCALE = [ALFA_RED, "#FF6B61", "#FF9E8D", "#FFD1C9", "#FFE8E5"]
ALFA_SEQUENTIAL = ["#EF3124", "#F25D52", "#F68A82", "#F9B6B1", "#FCE3E1"]
ALFA_VIRIDIS_CUSTOM = ["#440154", "#414487", "#2A788E", "#22A884", "#7AD151", "#FDE725"]

def prepare_commit_data(commits):
    """Преобразует данные коммитов в DataFrame для анализа"""
    commit_data = []
    for commit in commits:
        commit_date = commit['date'].date() if isinstance(commit['date'], datetime) else commit['date']
        commit_data.append({
            'date': commit_date,
            'additions': commit['stats']['additions'],
            'deletions': commit['stats']['deletions'],
            'files_changed': len(commit['files']),
            'total_changes': commit['stats']['additions'] + commit['stats']['deletions'],
            'hour': commit['date'].hour if isinstance(commit['date'], datetime) else 0,
            'day_of_week': commit['date'].strftime('%A') if isinstance(commit['date'], datetime) else 'Unknown',
            'message': commit['message'].splitlines()[0] if commit['message'] else "No message",
            'commit_url': commit['url'],
            'sha': commit['sha'][:7]
        })
    
    return pd.DataFrame(commit_data)

def create_daily_activity_chart(df_commits, author_name):
    """Создает график активности по дням"""
    # Группируем данные по дате
    daily_activity = df_commits.groupby('date').agg({
        'date': 'count',
        'additions': 'sum',
        'deletions': 'sum',
        'files_changed': 'sum'
    }).rename(columns={'date': 'commits'}).reset_index()
    
    # Создаем интерактивный график активности по дням
    fig_daily = px.bar(
        daily_activity,
        x='date',
        y='commits',
        labels={'date': 'Date', 'commits': 'Number of Commits'},
        title=f'Daily Activity',
        color_discrete_sequence=[ALFA_RED]
    )
    
    # Добавляем линию тренда
    fig_daily.add_trace(
        go.Scatter(
            x=daily_activity['date'],
            y=daily_activity['commits'].rolling(window=3, min_periods=1).mean(),
            mode='lines',
            name='3-day Average',
            line=dict(color=ALFA_BLACK, width=2, dash='dot')
        )
    )
    
    # Настраиваем макет
    fig_daily.update_layout(
        xaxis_title='Date',
        yaxis_title='Number of Commits',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    # Настраиваем оси
    fig_daily.update_xaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor=ALFA_LIGHT_GRAY,
        zeroline=False
    )
    fig_daily.update_yaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor=ALFA_LIGHT_GRAY,
        zeroline=False
    )
    
    return fig_daily

def create_weekly_activity_chart(df_commits):
    """Создает график активности по дням недели"""
    # Определяем порядок дней недели для правильной сортировки
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Группируем по дню недели
    day_of_week_counts = df_commits['day_of_week'].value_counts().reindex(days_order).fillna(0)
    
    # Создаем график с цветами в стиле Альфа
    fig_day_of_week = px.bar(
        x=day_of_week_counts.index,
        y=day_of_week_counts.values,
        labels={'x': 'Day of Week', 'y': 'Number of Commits'},
        title='Weekly Patterns',
        color=day_of_week_counts.values,
        color_continuous_scale=ALFA_SEQUENTIAL
    )
    
    # Настраиваем формат подсказок
    fig_day_of_week.update_traces(
        hovertemplate='<b>%{x}</b><br>Commits: %{y}<extra></extra>'
    )
    
    # Настраиваем макет
    fig_day_of_week.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    # Настраиваем оси
    fig_day_of_week.update_xaxes(
        showgrid=False,
        zeroline=False
    )
    fig_day_of_week.update_yaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor=ALFA_LIGHT_GRAY,
        zeroline=False
    )
    
    return fig_day_of_week

def create_activity_heatmap(df_commits):
    """Создает тепловую карту активности"""
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Создаем сводную таблицу: дни недели vs часы
    heatmap_data = pd.crosstab(df_commits['day_of_week'], df_commits['hour'])
    
    # Переупорядочиваем строки, чтобы дни недели шли в правильном порядке
    if set(days_order).issubset(set(heatmap_data.index)):
        heatmap_data = heatmap_data.reindex(days_order)
    
    # Создаем тепловую карту с кастомными цветами
    fig_heatmap = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Commits"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        color_continuous_scale=ALFA_SEQUENTIAL,
        title="Activity Heatmap"
    )
    
    # Настраиваем макет
    fig_heatmap.update_layout(
        xaxis=dict(tickmode='linear'),
        yaxis=dict(tickmode='linear'),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    return fig_heatmap

def create_code_changes_chart(df_commits):
    """Создает график изменений кода по времени"""
    # Создаем фрейм данных с накопленными изменениями по дням
    code_changes = df_commits.groupby('date').agg({
        'additions': 'sum',
        'deletions': 'sum'
    }).reset_index()
    
    # Преобразуем в формат для Plotly
    code_changes_long = pd.melt(
        code_changes, 
        id_vars=['date'], 
        value_vars=['additions', 'deletions'],
        var_name='change_type', 
        value_name='lines'
    )
    
    # Создаем график с корпоративными цветами
    fig_changes = px.area(
        code_changes_long,
        x='date',
        y='lines',
        color='change_type',
        labels={'date': 'Date', 'lines': 'Lines', 'change_type': 'Change Type'},
        title='Code Changes Over Time',
        color_discrete_map={'additions': '#4CAF50', 'deletions': ALFA_RED}
    )
    
    # Настраиваем режим наведения и стиль
    fig_changes.update_layout(
        hovermode="x unified",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    # Настраиваем оси
    fig_changes.update_xaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor=ALFA_LIGHT_GRAY,
        zeroline=False
    )
    fig_changes.update_yaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor=ALFA_LIGHT_GRAY,
        zeroline=False
    )
    
    return fig_changes

def create_file_types_chart(commits):
    """Создает круговую диаграмму типов файлов"""
    # Собираем расширения файлов
    file_extensions = []
    for commit in commits:
        for file in commit['files']:
            if isinstance(file, dict) and 'filename' in file:
                _, ext = os.path.splitext(file['filename'])
                if ext:  # Если есть расширение
                    file_extensions.append(ext.lower())
    
    # Считаем частоту каждого расширения
    extension_counts = Counter(file_extensions)
    
    # Берем топ-10 расширений, остальные группируем как "Other"
    top_extensions = dict(extension_counts.most_common(10))
    if len(extension_counts) > 10:
        top_extensions['Other'] = sum(count for ext, count in extension_counts.items() 
                                     if ext not in top_extensions)
    
    # Создаем круговую диаграмму с корпоративными цветами
    fig_extensions = px.pie(
        values=list(top_extensions.values()),
        names=list(top_extensions.keys()),
        title='File Types Distribution',
        hole=0.4,
        color_discrete_sequence=ALFA_VIRIDIS_CUSTOM
    )
    
    fig_extensions.update_traces(
        textposition='inside', 
        textinfo='percent+label'
    )
    
    # Настраиваем макет
    fig_extensions.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    return fig_extensions

def create_commits_calendar(df_commits):
    """Создает календарь коммитов (как в GitHub)"""
    # Подготавливаем данные для календаря
    calendar_data = df_commits.groupby('date').size().reset_index(name='count')
    
    # Создаем календарь с цветами в стиле Альфа
    fig = px.scatter(
        calendar_data,
        x='date',
        y=[1] * len(calendar_data),  # Все точки на одной линии
        size='count',  # Размер точки зависит от количества коммитов
        color='count',  # Цвет точки зависит от количества коммитов
        color_continuous_scale=ALFA_SEQUENTIAL,
        size_max=20,
        title='Commit Calendar'
    )
    
    # Настраиваем макет
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='',
        yaxis=dict(
            showticklabels=False,
            showgrid=False,
            zeroline=False
        ),
        height=180,  # Делаем график компактным
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
        coloraxis_showscale=False,  # Скрываем шкалу цветов
    )
    
    # Настраиваем подсказки
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>Commits: %{marker.size}<extra></extra>'
    )
    
    return fig

def display_commit_analytics(commits, author_data):
    """Отображает аналитику коммитов в Streamlit"""
    if not commits:
        st.info("No commits found for the selected period")
        return
    
    # Применяем стилизацию к Streamlit
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        color: #333333;
        font-size: 14px;
        font-weight: 400;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EF3124 !important;
        color: white !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #EF3124;
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
    }
    h1, h2, h3 {
        color: #333333;
    }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #E5E5E5;
    }
    .css-1ht1j8u {
        overflow-x: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Создаем красивый заголовок с иконкой и метриками
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1rem;">
        <div style="font-size: 2.5rem; margin-right: 10px;">👨‍💻</div>
        <div>
            <h2 style="margin: 0; padding: 0;">{author_data["name"]}</h2>
            <div style="color: #666; font-size: 1rem;">
                {author_data.get("github_login", "")} • {author_data.get("email", "")}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Преобразуем данные в DataFrame
    df_commits = prepare_commit_data(commits)
    
    # Отображаем ключевые метрики в красивых карточках
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Commits", 
            len(commits),
            delta=None
        )
    
    with col2:
        total_additions = df_commits['additions'].sum()
        st.metric(
            "Lines Added", 
            f"{total_additions:,}",
            delta=None
        )
    
    with col3:
        total_deletions = df_commits['deletions'].sum()
        st.metric(
            "Lines Deleted", 
            f"{total_deletions:,}",
            delta=None
        )
    
    with col4:
        total_files = df_commits['files_changed'].sum()
        st.metric(
            "Files Changed", 
            f"{total_files:,}",
            delta=None
        )
    
    # Добавляем компактный календарь коммитов вверху
    calendar = create_commits_calendar(df_commits)
    st.plotly_chart(calendar, use_container_width=True)
    
    # Добавляем стилизованные вкладки для разных категорий графиков
    viz_tabs = st.tabs(["Activity", "Code Changes", "File Analysis"])
    
    with viz_tabs[0]:
        # Графики активности
        col1, col2 = st.columns(2)
        
        with col1:
            daily_chart = create_daily_activity_chart(df_commits, author_data["name"])
            st.plotly_chart(daily_chart, use_container_width=True)
        
        with col2:
            weekly_chart = create_weekly_activity_chart(df_commits)
            st.plotly_chart(weekly_chart, use_container_width=True)
        
        # Тепловая карта активности
        if 'hour' in df_commits.columns and 'day_of_week' in df_commits.columns:
            heatmap = create_activity_heatmap(df_commits)
            st.plotly_chart(heatmap, use_container_width=True)
    
    with viz_tabs[1]:
        # График изменений кода
        changes_chart = create_code_changes_chart(df_commits)
        st.plotly_chart(changes_chart, use_container_width=True)
        
        # Добавляем статистику по изменениям кода
        col1, col2 = st.columns(2)
        
        with col1:
            # Вычисляем статистику по неделям
            df_commits['week'] = pd.to_datetime(df_commits['date']).dt.isocalendar().week
            weekly_stats = df_commits.groupby('week').agg({
                'additions': 'sum',
                'deletions': 'sum',
                'files_changed': 'sum'
            }).reset_index()
            
            st.markdown("### Weekly Code Change Statistics")
            st.dataframe(
                weekly_stats,
                column_config={
                    "week": st.column_config.NumberColumn("Week"),
                    "additions": st.column_config.NumberColumn("Added", format="%d"),
                    "deletions": st.column_config.NumberColumn("Deleted", format="%d"),
                    "files_changed": st.column_config.NumberColumn("Files", format="%d")
                },
                hide_index=True,
                use_container_width=True
            )
        
        with col2:
            # Вычисляем соотношение добавленных/удаленных строк
            if total_additions + total_deletions > 0:
                add_ratio = total_additions / (total_additions + total_deletions) * 100
                del_ratio = 100 - add_ratio
                
                st.markdown("### Code Change Ratio")
                st.markdown(f"""
                <div style="display: flex; height: 30px; width: 100%; background-color: #F5F5F5; border-radius: 5px; overflow: hidden; margin-top: 10px;">
                    <div style="width: {add_ratio}%; background-color: #4CAF50; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {add_ratio:.1f}%
                    </div>
                    <div style="width: {del_ratio}%; background-color: #EF3124; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {del_ratio:.1f}%
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <div>Added</div>
                    <div>Deleted</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Средний размер коммита
                avg_changes = (total_additions + total_deletions) / len(commits)
                st.markdown(f"**Average changes per commit:** {avg_changes:.1f} lines")
    
    with viz_tabs[2]:
        # Анализ типов файлов
        if commits[0].get('files'):
            col1, col2 = st.columns([3, 2])
            
            with col1:
                file_types_chart = create_file_types_chart(commits)
                st.plotly_chart(file_types_chart, use_container_width=True)
            
            with col2:
                # Собираем топ измененных файлов
                file_changes = {}
                for commit in commits:
                    for file in commit['files']:
                        if isinstance(file, dict) and 'filename' in file:
                            filename = file['filename']
                            changes = file.get('additions', 0) + file.get('deletions', 0)
                            
                            if filename in file_changes:
                                file_changes[filename] += changes
                            else:
                                file_changes[filename] = changes
                
                # Сортируем и берем топ-10
                top_files = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)[:10]
                
                st.markdown("### Most Changed Files")
                for file, changes in top_files:
                    # Определяем иконку для файла
                    icon = "📄"
                    if file.endswith(('.py', '.java', '.js', '.ts', '.cpp')):
                        icon = "🧩"
                    elif file.endswith(('.md', '.txt')):
                        icon = "📝"
                    elif file.endswith(('.json', '.yaml', '.yml', '.xml')):
                        icon = "⚙️"
                    elif file.endswith(('.html', '.css')):
                        icon = "🎨"
                    
                    # Сокращаем длинные имена файлов
                    display_name = file
                    if len(file) > 40:
                        parts = file.split('/')
                        if len(parts) > 2:
                            display_name = f"{parts[0]}/.../{parts[-1]}"
                    
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                        <div style="flex: 0 0 30px; font-size: 1.2rem;">{icon}</div>
                        <div style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{file}">{display_name}</div>
                        <div style="flex: 0 0 80px; text-align: right; font-weight: bold;">{changes} lines</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Добавляем интерактивную таблицу с коммитами
    st.markdown("### 📋 Recent Commits")
    
    # Создаем красивую таблицу коммитов
    for i, row in df_commits.sort_values('date', ascending=False).head(10).iterrows():
        commit_date = row['date']
        commit_msg = row['message']
        commit_url = row['commit_url']
        commit_sha = row['sha']
        
        # Ограничиваем длину сообщения
        if len(commit_msg) > 70:
            commit_msg = commit_msg[:67] + "..."
        
        st.markdown(f"""
        <div style="display: flex; padding: 12px; border-radius: 8px; background-color: {ALFA_GRAY}; margin-bottom: 8px; align-items: center;">
            <div style="flex: 0 0 100px; color: #666;">{commit_date}</div>
            <div style="flex: 1; font-weight: 500;">{commit_msg}</div>
            <div style="flex: 0 0 100px; text-align: right;">
                <a href="{commit_url}" target="_blank" style="text-decoration: none; color: {ALFA_RED}; font-family: monospace;">{commit_sha}</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Добавляем кнопку для просмотра всех коммитов
    if len(df_commits) > 10:
        show_all = st.button("Show All Commits", type="secondary")
        
        if show_all:
            st.dataframe(
                df_commits[['date', 'message', 'additions', 'deletions', 'files_changed', 'sha', 'commit_url']],
                column_config={
                    "date": "Date",
                    "message": "Message",
                    "additions": st.column_config.NumberColumn("Added", format="%d"),
                    "deletions": st.column_config.NumberColumn("Deleted", format="%d"),
                    "files_changed": st.column_config.NumberColumn("Files", format="%d"),
                    "sha": "SHA",
                    "commit_url": st.column_config.LinkColumn("Link")
                },
                hide_index=True,
                use_container_width=True
            )