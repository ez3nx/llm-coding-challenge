import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import streamlit as st
import numpy as np
import colorsys

# Корпоративные цвета Альфа Банка
ALFA_RED = "#EF3124"
ALFA_BLACK = "#333333"
ALFA_GRAY = "#F5F5F5"
ALFA_LIGHT_GRAY = "#E5E5E5"

# Расширенная цветовая палитра для графиков
ALFA_COLOR_SCALE = [ALFA_RED, "#FF6B61", "#FF9E8D", "#FFD1C9", "#FFE8E5"]
ALFA_SEQUENTIAL = ["#EF3124", "#F25D52", "#F68A82", "#F9B6B1", "#FCE3E1"]
ALFA_VIRIDIS_CUSTOM = ["#440154", "#414487", "#2A788E", "#22A884", "#7AD151", "#FDE725"]

def generate_color_palette(base_color, num_colors=10):
    """Генерирует цветовую палитру на основе базового цвета"""

    r, g, b = int(base_color[1:3], 16)/255, int(base_color[3:5], 16)/255, int(base_color[5:7], 16)/255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    
    palette = []
    for i in range(num_colors):

        new_s = max(0.2, s - (i * 0.08))
        new_v = min(0.95, v + (i * 0.05))
        new_r, new_g, new_b = colorsys.hsv_to_rgb(h, new_s, new_v)

        hex_color = f"#{int(new_r*255):02x}{int(new_g*255):02x}{int(new_b*255):02x}"
        palette.append(hex_color)
    
    return palette

ALFA_EXTENDED_PALETTE = generate_color_palette(ALFA_RED, 20)

def prepare_commit_data(commits):
    """Преобразует данные коммитов в DataFrame для анализа с расширенными метриками"""
    commit_data = []
    for commit in commits:
        commit_date = (
            commit["date"].date()
            if isinstance(commit["date"], datetime)
            else commit["date"]
        )
        commit_time = (
            commit["date"].time()
            if isinstance(commit["date"], datetime)
            else datetime.min.time()
        )
        
        # Расчет дополнительных метрик
        additions = commit["stats"]["additions"]
        deletions = commit["stats"]["deletions"]
        files_changed = len(commit["files"])
        total_changes = additions + deletions
        
        # Рассчитываем сложность изменений (соотношение изменений к файлам)
        complexity = total_changes / max(1, files_changed)
        
        # Определяем тип коммита на основе соотношения добавлений/удалений
        if additions == 0 and deletions > 0:
            commit_type = "Removal"
        elif deletions == 0 and additions > 0:
            commit_type = "Addition"
        elif additions > deletions * 3:
            commit_type = "Major Addition"
        elif deletions > additions * 3:
            commit_type = "Major Removal"
        else:
            commit_type = "Modification"
        
        commit_data.append(
            {
                "date": commit_date,
                "time": commit_time,
                "datetime": commit["date"] if isinstance(commit["date"], datetime) else datetime.combine(commit_date, commit_time),
                "additions": additions,
                "deletions": deletions,
                "files_changed": files_changed,
                "total_changes": total_changes,
                "complexity": complexity,
                "commit_type": commit_type,
                "hour": (
                    commit["date"].hour if isinstance(commit["date"], datetime) else 0
                ),
                "day_of_week": (
                    commit["date"].strftime("%A")
                    if isinstance(commit["date"], datetime)
                    else "Unknown"
                ),
                "week_of_year": (
                    commit["date"].isocalendar()[1]
                    if isinstance(commit["date"], datetime)
                    else 0
                ),
                "month": (
                    commit["date"].strftime("%B")
                    if isinstance(commit["date"], datetime)
                    else "Unknown"
                ),
                "message": (
                    commit["message"].splitlines()[0]
                    if commit["message"]
                    else "No message"
                ),
                "commit_url": commit["url"],
                "sha": commit["sha"][:7],
                # Добавляем LLM резюме
                "llm_summary": commit.get("llm_summary", ""),
            }
        )
    
    df = pd.DataFrame(commit_data)

    if len(df) > 1:
        df = df.sort_values('datetime')
        df['additions_ma7'] = df['additions'].rolling(window=7, min_periods=1).mean()
        df['deletions_ma7'] = df['deletions'].rolling(window=7, min_periods=1).mean()
        df['changes_ma7'] = df['total_changes'].rolling(window=7, min_periods=1).mean()
    
    return df

def create_enhanced_daily_activity_chart(df_commits):
    """Создает улучшенный график активности по дням без анимации"""
    # Группируем данные по дате
    daily_activity = (
        df_commits.groupby("date")
        .agg(
            {
                "date": "count",
                "additions": "sum",
                "deletions": "sum",
                "files_changed": "sum",
                "complexity": "mean",
            }
        )
        .rename(columns={"date": "commits"})
        .reset_index()
    )

    daily_activity['bubble_size'] = np.sqrt(daily_activity['commits'] * 5) + 10

    fig = px.scatter(
        daily_activity,
        x="date",
        y="commits",
        size="bubble_size",
        color="complexity",
        color_continuous_scale=px.colors.sequential.Reds,
        hover_name="date",
        hover_data={
            "bubble_size": False,
            "commits": True,
            "additions": True,
            "deletions": True,
            "files_changed": True,
            "complexity": ":.2f"
        },
        labels={
            "date": "Date", 
            "commits": "Number of Commits", 
            "complexity": "Avg. Complexity"
        },
        title="Daily Activity with Complexity",
    )
    
    # Настраиваем макет
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Number of Commits",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    # Настраиваем оси
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        rangeslider=dict(visible=True, thickness=0.05)  # Добавляем слайдер диапазона дат
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False
    )
    
    return fig

def create_weekly_activity_chart(df_commits):
    """Создает график активности по дням недели без детализации по типам коммитов"""
    # Определяем порядок дней недели для правильной сортировки
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    
    # Группируем по дню недели без детализации по типам коммитов
    day_of_week_counts = df_commits["day_of_week"].value_counts().reindex(days_order).fillna(0)
    
    # Создаем график с цветами в стиле Альфа
    fig = px.bar(
        x=day_of_week_counts.index,
        y=day_of_week_counts.values,
        labels={"x": "Day of Week", "y": "Number of Commits"},
        title="Weekly Patterns",
        color=day_of_week_counts.values,
        color_continuous_scale=ALFA_SEQUENTIAL,
    )
    
    # Настраиваем формат подсказок
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Commits: %{y}<extra></extra>"
    )
    
    # Настраиваем макет
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    # Настраиваем оси
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False
    )
    
    return fig

def create_activity_heatmap(df_commits):
    """Создает двумерную тепловую карту активности"""
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    
    # Создаем сводную таблицу: дни недели vs часы
    heatmap_data = pd.crosstab(df_commits["day_of_week"], df_commits["hour"])
    
    # Переупорядочиваем строки, чтобы дни недели шли в правильном порядке
    if set(days_order).issubset(set(heatmap_data.index)):
        heatmap_data = heatmap_data.reindex(days_order)
    
    # Создаем улучшенную тепловую карту с кастомными цветами
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Hour of Day", y="Day of Week", color="Commits"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        color_continuous_scale=ALFA_SEQUENTIAL,
        title="Activity Heatmap",
        aspect="auto"  # Для лучшего соотношения сторон
    )
    
    # Добавляем текст значений в ячейки для лучшей читаемости
    for i, day in enumerate(heatmap_data.index):
        for j, hour in enumerate(heatmap_data.columns):
            value = heatmap_data.iloc[i, j]
            if value > 0:  # Показываем только ненулевые значения
                fig.add_annotation(
                    x=hour,
                    y=day,
                    text=str(value),
                    showarrow=False,
                    font=dict(
                        color="white" if value > 3 else "black",  # Адаптивный цвет текста
                        size=9
                    )
                )
    
    # Настраиваем макет
    fig.update_layout(
        xaxis=dict(
            tickmode="linear",
            tick0=0,
            dtick=2,  # Показывать каждый второй час для меньшей загруженности
            title_font=dict(size=14),
        ),
        yaxis=dict(
            tickmode="linear",
            title_font=dict(size=14),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
        coloraxis_colorbar=dict(
            title="Commits",
            thicknessmode="pixels", thickness=20,
            lenmode="pixels", len=300,
            yanchor="top", y=1,
            xanchor="right", x=1.02,
        ),
    )
    
    return fig

def create_enhanced_code_changes_chart(df_commits):
    """Создает улучшенный график изменений кода по времени без анимации"""
    # Создаем фрейм данных с накопленными изменениями по дням
    code_changes = (
        df_commits.groupby("date")
        .agg({
            "additions": "sum", 
            "deletions": "sum",
            "files_changed": "sum",
            "complexity": "mean"
        })
        .reset_index()
    )
    
    # Добавляем кумулятивные суммы
    code_changes['cumulative_additions'] = code_changes['additions'].cumsum()
    code_changes['cumulative_deletions'] = code_changes['deletions'].cumsum()
    
    # Создаем subplot с двумя графиками
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Daily Code Changes", "Cumulative Code Growth"),
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.4, 0.6]
    )
    
    # 2. Кумулятивный рост (нижний график)
    fig.add_trace(
        go.Scatter(
            x=code_changes["date"],
            y=code_changes["cumulative_additions"],
            name="Cumulative Additions",
            line=dict(color="#4CAF50", width=2),
            fill="tozeroy",
            fillcolor="rgba(76, 175, 80, 0.2)",
            hovertemplate="<b>%{x}</b><br>Total Additions: %{y}<extra></extra>"
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=code_changes["date"],
            y=code_changes["cumulative_deletions"],
            name="Cumulative Deletions",
            line=dict(color=ALFA_RED, width=2),
            fill="tozeroy",
            fillcolor=f'rgba({int(ALFA_RED[1:3], 16)}, {int(ALFA_RED[3:5], 16)}, {int(ALFA_RED[5:7], 16)}, 0.2)',
            hovertemplate="<b>%{x}</b><br>Total Deletions: %{y}<extra></extra>"
        ),
        row=2, col=1
    )
    
    # Добавляем линию чистого изменения
    fig.add_trace(
        go.Scatter(
            x=code_changes["date"],
            y=code_changes["cumulative_additions"] - code_changes["cumulative_deletions"],
            name="Net Code Growth",
            line=dict(color="#2196F3", width=3),
            hovertemplate="<b>%{x}</b><br>Net Code: %{y}<extra></extra>"
        ),
        row=2, col=1
    )
    
    # Настраиваем макет
    fig.update_layout(
        title="Code Changes Analysis",
        barmode="overlay",  # Накладываем столбцы для наглядности
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=80, b=10),
        height=600,
    )
    
    # Настраиваем оси
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        rangeslider=dict(visible=True, thickness=0.05),
        row=2, col=1
    )
    
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text="Lines Changed",
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text="Cumulative Lines",
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        row=2, col=1
    )
    
    return fig

def create_interactive_file_types_chart(commits):
    """Создает интерактивную визуализацию типов файлов"""
    # Собираем расширения файлов и их изменения
    file_data = []
    for commit in commits:
        for file in commit["files"]:
            if isinstance(file, dict) and "filename" in file:
                _, ext = os.path.splitext(file["filename"])
                if ext:  # Если есть расширение
                    ext = ext.lower()
                    additions = file.get("additions", 0)
                    deletions = file.get("deletions", 0)
                    changes = additions + deletions
                    commit_date = commit["date"].date() if isinstance(commit["date"], datetime) else commit["date"]
                    
                    file_data.append({
                        "extension": ext,
                        "filename": file["filename"],
                        "additions": additions,
                        "deletions": deletions,
                        "changes": changes,
                        "date": commit_date
                    })
    
    if not file_data:
        return None
        
    # Создаем DataFrame
    df_files = pd.DataFrame(file_data)
    
    # Группируем по расширению
    ext_summary = df_files.groupby("extension").agg({
        "changes": "sum",
        "additions": "sum",
        "deletions": "sum",
        "filename": "count"
    }).reset_index()
    
    ext_summary = ext_summary.rename(columns={"filename": "count"})
    ext_summary = ext_summary.sort_values("changes", ascending=False).head(15)
    
    # Создаем интерактивную визуализацию
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"type": "pie"}]],
        subplot_titles=("File Types Distribution")
    )
    
    # Добавляем интерактивную круговую диаграмму
    fig.add_trace(
        go.Pie(
            labels=ext_summary["extension"],
            values=ext_summary["count"],
            textinfo="percent+label",
            hole=0.5,
            marker=dict(colors=ALFA_SEQUENTIAL),  # Изменить на ALFA_SEQUENTIAL вместо ALFA_VIRIDIS_CUSTOM
            hovertemplate="<b>%{label}</b><br>Files: %{value}<br>Percentage: %{percent}<extra></extra>",
            pull=[0.1 if i == 0 else 0 for i in range(len(ext_summary))],  # Выделяем первый сегмент
            domain=dict(x=[0, 0.48]),
        ),
        row=1, col=1
    )
    
    
    # Настраиваем макет
    fig.update_layout(
        title="File Types Analysis",
        # updatemenus=updatemenus,
        # barmode="stack",
        annotations=[
            dict(
                text="Bar Mode:",
                showarrow=False,
                x=0.42,
                y=1.2,
                xref="paper",
                yref="paper",
                font=dict(size=14)
            )
        ],
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=100, b=10),
        height=450,
    )
    
    
    return fig

def create_enhanced_commits_calendar(df_commits):
    """Создает улучшенный календарь коммитов без анимации"""
    # Подготавливаем данные для календаря
    calendar_data = df_commits.groupby("date").size().reset_index(name="count")
    
    # Добавляем информацию о дне недели для лучшей визуализации
    calendar_data["day_of_week"] = pd.to_datetime(calendar_data["date"]).dt.strftime("%A")
    
    # Создаем улучшенный календарь
    fig = px.scatter(
        calendar_data,
        x="date",
        y="day_of_week",
        size="count",
        color="count",
        color_continuous_scale=ALFA_SEQUENTIAL,
        size_max=25,
        hover_name="date",
        hover_data={
            "count": True,
            "day_of_week": True
        },
        title="Commit Calendar",
        category_orders={
            "day_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        },
    )
    
    # Настраиваем макет
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="",
        yaxis=dict(showticklabels=True, showgrid=True, gridcolor=ALFA_LIGHT_GRAY),
        height=250,  # Делаем график компактным
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
        coloraxis_showscale=False,  # Скрываем шкалу цветов
    )
    
    # Настраиваем подсказки
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Day: %{y}<br>Commits: %{marker.size}<extra></extra>"
    )
    
    return fig

def create_commit_impact_chart(df_commits):
    """Создает интерактивный график влияния коммитов без анимации"""
    # Вычисляем метрики влияния для каждого коммита
    impact_data = df_commits.copy()
    impact_data["impact"] = impact_data["total_changes"] * impact_data["complexity"] / 10
    
    # Сортируем по дате
    impact_data = impact_data.sort_values("datetime")
    
    # Создаем график с пузырьками, где размер отражает влияние
    fig = px.scatter(
        impact_data,
        x="datetime",
        y="total_changes",
        size="impact",
        color="commit_type",
        hover_name="message",
        hover_data={
            "sha": True,
            "additions": True,
            "deletions": True,
            "files_changed": True,
            "complexity": ":.2f",
            "impact": False,  # Скрываем в подсказке, так как это производное значение
        },
        labels={
            "datetime": "Date & Time", 
            "total_changes": "Lines Changed", 
            "commit_type": "Commit Type",
        },
        title="Commit Impact Analysis",
        size_max=40,
        color_discrete_sequence=ALFA_EXTENDED_PALETTE,
    )
    
    # Добавляем линию тренда
    fig.add_trace(
        go.Scatter(
            x=impact_data["datetime"],
            y=impact_data["total_changes"].rolling(window=5, min_periods=1).mean(),
            mode="lines",
            name="5-commit Moving Average",
            line=dict(color="#333333", width=2, dash="dot"),
        )
    )
    
    # Настраиваем макет
    fig.update_layout(
        xaxis_title="Date & Time",
        yaxis_title="Lines Changed",
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    # Настраиваем оси
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
    )
    
    return fig

def create_code_pulse_visualization(df_commits):
    """Создает визуализацию 'пульса кода' без анимации"""
    # Подготавливаем данные для визуализации
    pulse_data = df_commits.sort_values('datetime').copy()
    
    # Добавляем кумулятивные метрики
    pulse_data['cumulative_additions'] = pulse_data['additions'].cumsum()
    pulse_data['cumulative_deletions'] = pulse_data['deletions'].cumsum()
    pulse_data['net_changes'] = pulse_data['cumulative_additions'] - pulse_data['cumulative_deletions']
    
    # Рассчитываем скорость изменений (первая производная)
    pulse_data['change_velocity'] = pulse_data['total_changes'].rolling(window=5, min_periods=1).mean()
    
    # Создаем subplot с несколькими графиками
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Code Growth Over Time", "Change Velocity"),
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3]
    )
    
    # Добавляем линию кумулятивных добавлений
    fig.add_trace(
        go.Scatter(
            x=pulse_data['datetime'],
            y=pulse_data['cumulative_additions'],
            mode='lines',
            name='Cumulative Additions',
            line=dict(color='#4CAF50', width=2),
            fill='tozeroy',
            fillcolor='rgba(76, 175, 80, 0.2)',
        ),
        row=1, col=1
    )
    
    # Добавляем линию кумулятивных удалений
    fig.add_trace(
        go.Scatter(
            x=pulse_data['datetime'],
            y=pulse_data['cumulative_deletions'],
            mode='lines',
            name='Cumulative Deletions',
            line=dict(color=ALFA_RED, width=2),
            fill='tozeroy',
            fillcolor=f'rgba({int(ALFA_RED[1:3], 16)}, {int(ALFA_RED[3:5], 16)}, {int(ALFA_RED[5:7], 16)}, 0.2)',
        ),
        row=1, col=1
    )
    
    # Добавляем линию чистого изменения
    fig.add_trace(
        go.Scatter(
            x=pulse_data['datetime'],
            y=pulse_data['net_changes'],
            mode='lines',
            name='Net Code Growth',
            line=dict(color='#2196F3', width=3),
        ),
        row=1, col=1
    )
    
    # Добавляем маркеры фактических коммитов
    fig.add_trace(
        go.Scatter(
            x=pulse_data['datetime'],
            y=pulse_data['net_changes'],
            mode='markers',
            name='Commits',
            marker=dict(
                color=pulse_data['commit_type'].map({
                    "Addition": "#4CAF50",
                    "Major Addition": "#2E7D32",
                    "Modification": "#FF9800",
                    "Removal": "#F44336",
                    "Major Removal": "#B71C1C"                }),
                size=pulse_data['total_changes'] / pulse_data['total_changes'].max() * 15 + 5,
                symbol='circle',
                line=dict(width=1, color='#333333'),
            ),
            hovertemplate='<b>%{text}</b><br>Date: %{x}<br>Net Code: %{y}<br>Changes: %{customdata[0]}<extra></extra>',
            text=pulse_data['message'],
            customdata=pulse_data[['total_changes', 'sha']],
            showlegend=False,
        ),
        row=1, col=1
    )
    
    
    # Настраиваем макет
    fig.update_layout(
        title='Code Pulse Visualization',
        hovermode='closest',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Arial, sans-serif', size=12, color=ALFA_BLACK),
        margin=dict(l=10, r=10, t=80, b=10),
        height=600,
    )
    
    # Настраиваем оси
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        rangeslider=dict(visible=True, thickness=0.05),
        row=2, col=1
    )
    
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text='Lines of Code',
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text='Lines/Commit',
        showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
        row=2, col=1
    )
    
    return fig

def display_commit_analytics(commits, author_data):
    """Отображает аналитику коммитов в Streamlit с улучшенной визуализацией без анимации"""
    if not commits:
        st.info("No commits found for the selected period")
        return
    
    # Применяем стилизацию к Streamlit
    st.markdown(
        """
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
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #EF3124 !important;
        color: white !important;
        font-weight: bold !important;
        transform: translateY(-3px);
        box-shadow: 0 4px 10px rgba(239, 49, 36, 0.2);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #FFEBE9;
        transform: translateY(-2px);
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #EF3124;
        font-weight: 700;
        transition: all 0.3s ease;
    }
    div[data-testid="stMetricValue"]:hover {
        transform: scale(1.05);
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
        transition: all 0.3s ease;
    }
    .stDataFrame:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    .css-1ht1j8u {
        overflow-x: auto;
    }
    .metric-card {
        background-color: #F5F5F5;
        border-radius: 10px;
        padding: 1rem;
        transition: all 0.3s ease;
        height: 100%;
    }
    .metric-card:hover {
        background-color: #FFEBE9;
        transform: translateY(-5px);
        box-shadow: 0 6px 15px rgba(239, 49, 36, 0.15);
    }
    .commit-card {
        transition: all 0.3s ease;
    }
    .commit-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
    
    # Создаем красивый заголовок с иконкой и метриками
    st.markdown(
        f"""
    <div style="display: flex; align-items: center; margin-bottom: 1rem; background-color: #F5F5F5; padding: 1.5rem; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
        <div style="font-size: 3rem; margin-right: 20px; color: #EF3124;">👨‍💻</div>
        <div style="flex-grow: 1;">
            <h2 style="margin: 0; padding: 0; font-size: 1.8rem;">{author_data["name"]}</h2>
            <div style="color: #666; font-size: 1.1rem; margin-top: 5px;">
                {author_data.get("github_login", "")} • {author_data.get("email", "")}
            </div>
        </div>
        <div style="background-color: #EF3124; color: white; padding: 0.5rem 1rem; border-radius: 30px; font-weight: bold; display: flex; align-items: center;">
            <span style="margin-right: 5px;">⭐</span> Commit Analytics
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    
    # Преобразуем данные в DataFrame
    df_commits = prepare_commit_data(commits)
    
    # Отображаем ключевые метрики в красивых карточках
    st.markdown('<div style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">Total Commits</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #EF3124;">{len(commits)}</div>
            <div style="display: flex; align-items: center; margin-top: 0.5rem;">
                <div style="font-size: 1.2rem; margin-right: 5px;">📊</div>
                <div style="font-size: 0.8rem; color: #666;">Activity Metric</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    
    with col2:
        total_additions = df_commits["additions"].sum()
        st.markdown(
            f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">Lines Added</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #4CAF50;">{total_additions:,}</div>
            <div style="display: flex; align-items: center; margin-top: 0.5rem;">
                <div style="font-size: 1.2rem; margin-right: 5px;">➕</div>
                <div style="font-size: 0.8rem; color: #666;">Code Growth</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    
    with col3:
        total_deletions = df_commits["deletions"].sum()
        st.markdown(
            f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">Lines Deleted</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #EF3124;">{total_deletions:,}</div>
            <div style="display: flex; align-items: center; margin-top: 0.5rem;">
                <div style="font-size: 1.2rem; margin-right: 5px;">➖</div>
                <div style="font-size: 0.8rem; color: #666;">Code Reduction</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    
    with col4:
        total_files = df_commits["files_changed"].sum()
        st.markdown(
            f"""
        <div class="metric-card">
            <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.3rem;">Files Changed</div>
            <div style="font-size: 1.8rem; font-weight: 700; color: #2196F3;">{total_files:,}</div>
            <div style="display: flex; align-items: center; margin-top: 0.5rem;">
                <div style="font-size: 1.2rem; margin-right: 5px;">📁</div>
                <div style="font-size: 0.8rem; color: #666;">Scope Impact</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Добавляем компактный улучшенный календарь коммитов вверху
    calendar = create_enhanced_commits_calendar(df_commits)
    st.plotly_chart(calendar, use_container_width=True, config={"displayModeBar": False})
    
    # Добавляем стилизованные вкладки для разных категорий графиков
    viz_tabs = st.tabs(["📈 Activity", "🔄 Code Changes", "📁 File Analysis", "🔍 Impact Analysis", "📊 Advanced Metrics"])
    
    with viz_tabs[0]:
        # Графики активности без анимации
        st.markdown("### 📊 Developer Activity Patterns")
        
        col1, col2 = st.columns(2)
        with col1:
            daily_chart = create_enhanced_daily_activity_chart(df_commits)
            st.plotly_chart(daily_chart, use_container_width=True, config={"displayModeBar": True})
        
        with col2:
            weekly_chart = create_weekly_activity_chart(df_commits)
            st.plotly_chart(weekly_chart, use_container_width=True, config={"displayModeBar": True})
        

    
    with viz_tabs[1]:
        
        # Добавляем статистику по изменениям кода
        col1, col2 = st.columns(2)
        with col1:
            # Вычисляем статистику по неделям с интерактивным форматированием
            df_commits["week"] = pd.to_datetime(df_commits["date"]).dt.isocalendar().week
            weekly_stats = (
                df_commits.groupby("week")
                .agg({
                    "additions": "sum", 
                    "deletions": "sum", 
                    "files_changed": "sum",
                    "total_changes": "sum",
                    "complexity": "mean"
                })
                .reset_index()
            )
            
            # Добавляем столбец эффективности
            weekly_stats["efficiency"] = (weekly_stats["additions"] / weekly_stats["total_changes"] * 100).round(1)
            
            st.markdown("""
            <div style="background-color: #F5F5F5; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                <h4 style="margin-top: 0;">Weekly Code Change Statistics</h4>
                <p style="color: #666; margin-bottom: 0;">Breakdown of code changes by week with efficiency metrics</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Создаем интерактивную таблицу
            st.dataframe(
                weekly_stats,
                column_config={
                    "week": st.column_config.NumberColumn("Week", format="%d"),
                    "additions": st.column_config.NumberColumn("Added", format="%d"),
                                        "deletions": st.column_config.NumberColumn("Deleted", format="%d"),
                    "files_changed": st.column_config.NumberColumn("Files", format="%d"),
                    "total_changes": st.column_config.NumberColumn("Total", format="%d"),
                    "complexity": st.column_config.NumberColumn("Complexity", format="%.2f"),
                    "efficiency": st.column_config.ProgressColumn(
                        "Efficiency", 
                        format="%d%%",
                        min_value=0,
                        max_value=100,
                    ),
                },
                hide_index=True,
                use_container_width=True,
            )
        
        with col2:
            # Вычисляем соотношение добавленных/удаленных строк с улучшенным индикатором
            if total_additions + total_deletions > 0:
                add_ratio = total_additions / (total_additions + total_deletions) * 100
                del_ratio = 100 - add_ratio
                
                st.markdown("""
                <div style="background-color: #F5F5F5; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <h4 style="margin-top: 0;">Code Change Ratio</h4>
                    <p style="color: #666; margin-bottom: 0;">Balance between code additions and deletions</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(
                    f"""
                <div style="display: flex; height: 40px; width: 100%; background-color: #F5F5F5; border-radius: 5px; overflow: hidden; margin-top: 10px; position: relative;">
                    <div style="width: {add_ratio}%; background-color: #4CAF50; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {add_ratio:.1f}%
                    </div>
                    <div style="width: {del_ratio}%; background-color: #EF3124; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                        {del_ratio:.1f}%
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                    <div style="display: flex; align-items: center;"><div style="width: 12px; height: 12px; background-color: #4CAF50; border-radius: 50%; margin-right: 5px;"></div> Added</div>
                    <div style="display: flex; align-items: center;"><div style="width: 12px; height: 12px; background-color: #EF3124; border-radius: 50%; margin-right: 5px;"></div> Deleted</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
                
                # Средний размер коммита с визуальным индикатором
                avg_changes = (total_additions + total_deletions) / len(commits)
                avg_files = total_files / len(commits)
                
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                
                st.markdown("""
                <div style="background-color: #F5F5F5; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <h4 style="margin-top: 0;">Commit Size Metrics</h4>
                    <p style="color: #666; margin-bottom: 0;">Average size and complexity of commits</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    # Определяем размер коммита
                    size_category = "Large"
                    size_color = "#EF3124"
                    if avg_changes < 50:
                        size_category = "Small"
                        size_color = "#4CAF50"
                    elif avg_changes < 200:
                        size_category = "Medium"
                        size_color = "#FF9800"
                    
                    st.markdown(
                        f"""
                    <div style="background-color: #F8F8F8; padding: 1rem; border-radius: 8px; text-align: center;">
                        <div style="font-size: 0.9rem; color: #666;">Average Changes</div>
                        <div style="font-size: 1.8rem; font-weight: 700; color: {size_color};">{avg_changes:.1f}</div>
                        <div style="font-size: 0.9rem; color: #666; margin-top: 5px;">lines per commit</div>
                        <div style="margin-top: 10px; font-weight: 600; color: {size_color};">{size_category} Commits</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                
                with col2:
                    # Определяем сложность коммита по количеству файлов
                    complexity_category = "High"
                    complexity_color = "#EF3124"
                    if avg_files < 2:
                        complexity_category = "Low"
                        complexity_color = "#4CAF50"
                    elif avg_files < 5:
                        complexity_category = "Medium"
                        complexity_color = "#FF9800"
                    
                    st.markdown(
                        f"""
                    <div style="background-color: #F8F8F8; padding: 1rem; border-radius: 8px; text-align: center;">
                        <div style="font-size: 0.9rem; color: #666;">Average Scope</div>
                        <div style="font-size: 1.8rem; font-weight: 700; color: {complexity_color};">{avg_files:.1f}</div>
                        <div style="font-size: 0.9rem; color: #666; margin-top: 5px;">files per commit</div>
                        <div style="margin-top: 10px; font-weight: 600; color: {complexity_color};">{complexity_category} Complexity</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
    
    with viz_tabs[2]:
        # Анализ типов файлов с интерактивными элементами
        st.markdown("### 📂 File Types Distribution and Analysis")
        if commits[0].get("files"):
            # Интерактивная визуализация типов файлов
            file_types_chart = create_interactive_file_types_chart(commits)
            
            # Собираем топ измененных файлов
            file_changes = {}
            for commit in commits:
                for file in commit["files"]:
                    if isinstance(file, dict) and "filename" in file:
                        filename = file["filename"]
                        changes = file.get("additions", 0) + file.get("deletions", 0)
                        if filename in file_changes:
                            file_changes[filename] += changes
                        else:
                            file_changes[filename] = changes
            # Сортируем и берем топ-15
            top_files = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)[:15]
            
            # Создаем данные для горизонтальной диаграммы
            file_names = [os.path.basename(file) for file, _ in top_files]
            file_paths = [file for file, _ in top_files]
            file_changes_values = [changes for _, changes in top_files]
            # Определяем типы файлов для цветовой схемы
            file_types = []
            for file in file_paths:
                _, ext = os.path.splitext(file)
                if ext in ['.py', '.java', '.js', '.ts', '.jsx', '.tsx']:
                    file_types.append('Code')
                elif ext in ['.html', '.css', '.scss', '.less']:
                    file_types.append('UI')
                elif ext in ['.json', '.yaml', '.yml', '.xml', '.toml']:
                    file_types.append('Config')
                elif ext in ['.md', '.txt', '.csv', '.rst']:
                    file_types.append('Doc')
                else:
                    file_types.append('Other')
            
            # Отображаем диаграммы в двух колонках
            col1, col2 = st.columns(2)
            with col1:
                if file_types_chart:
                    st.plotly_chart(file_types_chart, use_container_width=True, config={"displayModeBar": False})
            
            with col2:
                # Создаем интерактивную горизонтальную гистограмму
                fig = px.bar(
                    x=file_changes_values,
                    y=file_names,
                    color=file_types,
                    orientation='h',
                    labels={'x': 'Lines Changed', 'y': 'File'},
                    title='Top Changed Files',
                    color_discrete_sequence=ALFA_SEQUENTIAL,
                    hover_data={'path': file_paths}
                )
                # Настраиваем макет с меньшей высотой
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Arial, sans-serif', size=12, color=ALFA_BLACK),
                    height=520,  # Увеличиваем высоту с 350 до 450
                    margin=dict(l=10, r=10, t=50, b=10),
                    yaxis={'categoryorder': 'total ascending'},
                    legend=dict(
                        title='File Type',
                        orientation='h',
                        yanchor='bottom',
                        y=1.02,
                        xanchor='right',
                        x=1
                    )
                )
                # Настраиваем подсказки
                fig.update_traces(
                    hovertemplate='<b>%{y}</b><br>Changes: %{x}<br>Path: %{customdata[0]}<br>Type: %{marker.color}<extra></extra>'
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                
    with viz_tabs[3]:
        # Анализ влияния коммитов
        st.markdown("### 🔍 Commit Impact Analysis")
        
        # График влияния коммитов
        impact_chart = create_commit_impact_chart(df_commits)
        st.plotly_chart(impact_chart, use_container_width=True, config={"displayModeBar": True})
        
        # Добавляем информацию о том, как интерпретировать
        st.markdown("""
        <div style="background-color: #F5F5F5; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-size: 1.2rem; margin-right: 10px;">ℹ️</div>
                <div style="font-weight: 600; color: #333;">About Impact Analysis</div>
            </div>
            <p style="margin: 0; color: #666;">
                The impact analysis visualizes the significance of each commit based on size (lines changed) and complexity (number of files and type of changes).
                                Larger bubbles represent commits with higher overall impact on the codebase.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Анализ типов коммитов
        st.markdown("### 📊 Commit Types Distribution")
        
        # Подсчитываем типы коммитов
        commit_types = df_commits['commit_type'].value_counts().reset_index()
        commit_types.columns = ['type', 'count']
        
        # Добавляем описания типов коммитов
        type_descriptions = {
            "Addition": "New code or features added",
            "Major Addition": "Significant new code or features",
            "Modification": "Balanced changes to existing code",
            "Removal": "Code cleanup or feature removal",
            "Major Removal": "Significant code removal or refactoring"
        }
        
        commit_types['description'] = commit_types['type'].map(type_descriptions)
        
        # Создаем интерактивную визуализацию
        fig = px.pie(
            commit_types,
            values='count',
            names='type',
            title='Commit Types Distribution',
            color='type',
            color_discrete_map={
                "Addition": "#4CAF50",
                "Major Addition": "#2E7D32",
                "Modification": "#FF9800",
                "Removal": "#F44336",
                "Major Removal": "#B71C1C"
            },
            hover_data=['description', 'count'],
        )
        
        # Настраиваем макет
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color=ALFA_BLACK),
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.2,
                xanchor='center',
                x=0.5
            )
        )
        
        # Настраиваем подсказки
        fig.update_traces(
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>%{customdata[0]}<br>Count: %{customdata[1]} (%{percent})<extra></extra>'
        )
        
        col1, col2 = st.columns([3, 2])
        with col1:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        
        with col2:
            # Добавляем объяснение типов коммитов
            st.markdown("<h4>Commit Type Definitions</h4>", unsafe_allow_html=True)
            
            for commit_type, description in type_descriptions.items():
                color = {
                    "Addition": "#4CAF50",
                    "Major Addition": "#2E7D32",
                    "Modification": "#FF9800",
                    "Removal": "#F44336",
                    "Major Removal": "#B71C1C"
                }.get(commit_type, "#333333")
                
                count = commit_types[commit_types['type'] == commit_type]['count'].values[0] if commit_type in commit_types['type'].values else 0
                percentage = (count / len(df_commits) * 100) if len(df_commits) > 0 else 0
                
                st.markdown(
                    f"""
                <div style="display: flex; align-items: center; margin-bottom: 0.8rem; background-color: #F8F8F8; padding: 0.8rem; border-radius: 8px;">
                    <div style="width: 15px; height: 15px; background-color: {color}; border-radius: 50%; margin-right: 10px;"></div>
                    <div style="flex-grow: 1;">
                        <div style="font-weight: 600;">{commit_type} ({count}, {percentage:.1f}%)</div>
                        <div style="font-size: 0.9rem; color: #666;">{description}</div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
    
    with viz_tabs[4]:
        # Продвинутые метрики и анализ
        st.markdown("### 📈 Developer Productivity Metrics")
        
        # Рассчитываем продвинутые метрики
        productivity_metrics = {}
        
        # Средний размер коммита
        productivity_metrics['avg_commit_size'] = df_commits['total_changes'].mean()
        
        # Среднее количество файлов на коммит
        productivity_metrics['avg_files_per_commit'] = df_commits['files_changed'].mean()
        
        # Коэффициент качества (соотношение добавлений к общим изменениям)
        productivity_metrics['quality_ratio'] = (df_commits['additions'].sum() / max(1, df_commits['total_changes'].sum())) * 100
        
        # Коэффициент сложности (средняя сложность коммитов)
        productivity_metrics['complexity'] = df_commits['complexity'].mean()
        
        # Частота коммитов (коммитов в день)
        if len(df_commits) > 0:
            date_range = (df_commits['date'].max() - df_commits['date'].min()).days + 1
            productivity_metrics['commit_frequency'] = len(df_commits) / max(1, date_range)
        else:
            productivity_metrics['commit_frequency'] = 0
            
        # Коэффициент изменения кода (соотношение изменений к количеству коммитов)
        productivity_metrics['code_churn_ratio'] = df_commits['total_changes'].sum() / max(1, len(df_commits))
        
        # Создаем радарный график продуктивности
        categories = ['Commit Size', 'Files per Commit', 'Quality Ratio', 'Complexity', 'Commit Frequency', 'Code Churn']
        
        # Нормализуем значения для радарного графика
        # Для некоторых метрик меньше значит лучше, для других - больше
        radar_values = [
            min(100, productivity_metrics['avg_commit_size'] / 2),  # Меньше лучше, ограничиваем 100
            min(100, productivity_metrics['avg_files_per_commit'] * 10),  # Меньше лучше, ограничиваем 100
            productivity_metrics['quality_ratio'],  # Больше лучше (0-100)
            min(100, productivity_metrics['complexity'] * 10),  # Меньше лучше, ограничиваем 100
            min(100, productivity_metrics['commit_frequency'] * 20),  # Больше лучше, ограничиваем 100
            min(100, productivity_metrics['code_churn_ratio'] / 5)  # Меньше лучше, ограничиваем 100
        ]
        
        # Инвертируем значения для метрик, где меньше значит лучше
        radar_values[0] = 100 - radar_values[0]
        radar_values[1] = 100 - radar_values[1]
        radar_values[3] = 100 - radar_values[3]
        radar_values[5] = 100 - radar_values[5]
        
        # Создаем радарный график
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=radar_values,
            theta=categories,
            fill='toself',
            name='Developer Metrics',
            line=dict(color=ALFA_RED),
            fillcolor=f'rgba({int(ALFA_RED[1:3], 16)}, {int(ALFA_RED[3:5], 16)}, {int(ALFA_RED[5:7], 16)}, 0.2)',
        ))
        
        # Добавляем эталонные значения
        fig.add_trace(go.Scatterpolar(
            r=[70, 70, 70, 70, 70, 70],  # Эталонные значения
            theta=categories,
            fill='toself',
            name='Reference',
            line=dict(color='#333333', dash='dot'),
            fillcolor='rgba(200, 200, 200, 0.2)',
        ))
        
        # Настраиваем макет
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                ),
                angularaxis=dict(
                    rotation=90,  # Начинаем с верхней точки
                    direction='clockwise'  # Направление по часовой стрелке
                )
            ),
            title='Developer Performance Radar',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.15,  # Смещаем легенду ниже
                xanchor='center',
                x=0.5
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color=ALFA_BLACK),
            margin=dict(l=80, r=80, t=50, b=80),  # Увеличиваем нижний отступ
            height=550,  # Увеличиваем высоту еще больше
        )
        
        col1, col2 = st.columns([3, 2])
        with col1:
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        
        with col2:
            # Добавляем объяснение метрик
            st.markdown("<h4>Productivity Metrics Explained</h4>", unsafe_allow_html=True)
            
            metrics_explanation = {
                "Commit Size": {
                    "value": f"{productivity_metrics['avg_commit_size']:.1f} lines",
                    "description": "Average number of lines changed per commit. Smaller, focused commits are generally better.",
                    "score": 100 - min(100, productivity_metrics['avg_commit_size'] / 2)
                },
                "Files per Commit": {
                    "value": f"{productivity_metrics['avg_files_per_commit']:.1f} files",
                    "description": "Average number of files changed in each commit. Lower values indicate more focused changes.",
                    "score": 100 - min(100, productivity_metrics['avg_files_per_commit'] * 10)
                },
                "Quality Ratio": {
                    "value": f"{productivity_metrics['quality_ratio']:.1f}%",
                    "description": "Percentage of additions relative to total changes. Higher values suggest more new code vs. rewrites.",
                    "score": productivity_metrics['quality_ratio']
                },
                "Complexity": {
                    "value": f"{productivity_metrics['complexity']:.2f}",
                    "description": "Average complexity of commits based on lines changed per file. Lower is better.",
                    "score": 100 - min(100, productivity_metrics['complexity'] * 10)
                },
                "Commit Frequency": {
                    "value": f"{productivity_metrics['commit_frequency']:.2f} per day",
                    "description": "Average number of commits per day. Higher values indicate more regular contributions.",
                    "score": min(100, productivity_metrics['commit_frequency'] * 20)
                },
                "Code Churn": {
                    "value": f"{productivity_metrics['code_churn_ratio']:.1f} lines/commit",
                    "description": "Rate of code changes relative to commit count. Lower values suggest more efficient changes.",
                    "score": 100 - min(100, productivity_metrics['code_churn_ratio'] / 5)
                }
            }
            
            for metric, data in metrics_explanation.items():
                # Определяем цвет на основе оценки
                if data["score"] >= 70:
                    color = "#4CAF50"  # Зеленый для хороших оценок
                elif data["score"] >= 40:
                    color = "#FF9800"  # Оранжевый для средних оценок
                else:
                    color = "#F44336"  # Красный для низких оценок
                
                st.markdown(
                    f"""
                <div style="margin-bottom: 0.8rem; background-color: #F8F8F8; padding: 0.8rem; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="font-weight: 600;">{metric}</div>
                        <div style="font-weight: 600; color: {color};">{data["score"]:.0f}/100</div>
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 500; margin: 5px 0;">{data["value"]}</div>
                    <div style="font-size: 0.9rem; color: #666;">{data["description"]}</div>
                    <div style="margin-top: 8px; height: 6px; background-color: #E0E0E0; border-radius: 3px;">
                        <div style="height: 100%; width: {data["score"]}%; background-color: {color}; border-radius: 3px;"></div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        
        # Добавляем анализ трендов
        st.markdown("### 📊 Trend Analysis")
        
        # Подготавливаем данные для анализа трендов
        trend_data = df_commits.sort_values('datetime').copy()
        
        # Добавляем скользящие средние и другие метрики трендов
        window_size = max(1, len(trend_data) // 10)  # Адаптивный размер окна
        
        # Добавляем скользящие средние для различных метрик
        trend_data['additions_ma'] = trend_data['additions'].rolling(window=window_size, min_periods=1).mean()
        trend_data['deletions_ma'] = trend_data['deletions'].rolling(window=window_size, min_periods=1).mean()
        trend_data['complexity_ma'] = trend_data['complexity'].rolling(window=window_size, min_periods=1).mean()
        trend_data['files_ma'] = trend_data['files_changed'].rolling(window=window_size, min_periods=1).mean()
        
        # Создаем интерактивный график трендов без анимации
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Code Changes Trend", "Complexity Trend", "Files Changed Trend", "Commit Size Distribution"),
            shared_xaxes=True,
            vertical_spacing=0.1,
            horizontal_spacing=0.1
        )
        
        # 1. Тренд изменений кода
        fig.add_trace(
            go.Scatter(
                x=trend_data['datetime'],
                y=trend_data['additions_ma'],
                mode='lines',
                name='Additions Trend',
                line=dict(color='#4CAF50', width=2),
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=trend_data['datetime'],
                y=trend_data['deletions_ma'],
                mode='lines',
                name='Deletions Trend',
                line=dict(color=ALFA_RED, width=2),
            ),
            row=1, col=1
        )
        
        # 2. Тренд сложности
        fig.add_trace(
            go.Scatter(
                x=trend_data['datetime'],
                y=trend_data['complexity_ma'],
                mode='lines',
                name='Complexity Trend',
                line=dict(color='#FF9800', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 152, 0, 0.2)',
            ),
            row=1, col=2
        )
        
        # 3. Тренд количества файлов
        fig.add_trace(
            go.Scatter(
                x=trend_data['datetime'],
                y=trend_data['files_ma'],
                mode='lines',
                name='Files Trend',
                line=dict(color='#2196F3', width=2),
                fill='tozeroy',
                fillcolor='rgba(33, 150, 243, 0.2)',
            ),
            row=2, col=1
        )
        
        # 4. Распределение размеров коммитов
        fig.add_trace(
            go.Histogram(
                x=trend_data['total_changes'],
                name='Commit Size',
                                marker=dict(color=ALFA_RED),
                nbinsx=20,
                histnorm='probability',
            ),
            row=2, col=2
        )
        
        # Настраиваем макет
        fig.update_layout(
            title='Developer Activity Trends',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.2,
                xanchor='center',
                x=0.5
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Arial, sans-serif', size=12, color=ALFA_BLACK),
            margin=dict(l=10, r=10, t=80, b=50),
            height=600,
        )
        
        # Настраиваем оси
        for i in range(1, 3):
            for j in range(1, 3):
                fig.update_xaxes(
                    showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
                    row=i, col=j
                )
                fig.update_yaxes(
                    showgrid=True, gridwidth=1, gridcolor=ALFA_LIGHT_GRAY, zeroline=False,
                    row=i, col=j
                )
        
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})
        
        # Добавляем выводы и рекомендации
        st.markdown("""
        <div style="background-color: #F5F5F5; padding: 1.2rem; border-radius: 8px; margin-top: 1.5rem;">
            <h4 style="margin-top: 0;">Summary and Recommendations</h4>
            <p style="color: #666;">
                Based on the analysis of commit patterns and code changes, here are some insights and recommendations:
            </p>
            <ul style="color: #666;">
                <li><strong>Code Quality:</strong> Consider the balance between additions and deletions in your commits. A healthy ratio suggests good code evolution.</li>
                <li><strong>Commit Size:</strong> Aim for smaller, more focused commits that are easier to review and less prone to introducing bugs.</li>
                <li><strong>Complexity Management:</strong> Monitor the complexity trend to ensure it stays manageable over time.</li>
                <li><strong>File Organization:</strong> Pay attention to which file types see the most changes, as this can indicate areas that might benefit from refactoring.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Добавляем интерактивную таблицу с коммитами
    st.markdown("### 📋 Recent Commits")
    
    # Получаем последние коммиты
    recent_commits = df_commits.sort_values("datetime", ascending=False).head(10)
    
    # Создаем красивую таблицу коммитов с экспандерами для LLM анализа и интерактивными элементами
    for i, row in recent_commits.iterrows():
        commit_date = row["date"]
        commit_time = row["time"]
        commit_msg = row["message"]
        commit_url = row["commit_url"]
        commit_sha = row["sha"]
        commit_type = row["commit_type"]
        llm_summary = row.get("llm_summary", "")
        
        # Определяем цвет для типа коммита
        type_colors = {
            "Addition": "#4CAF50",
            "Major Addition": "#2E7D32",
            "Modification": "#FF9800",
            "Removal": "#F44336",
            "Major Removal": "#B71C1C"
        }
        type_color = type_colors.get(commit_type, "#333333")
        
        # Ограничиваем длину сообщения
        if len(commit_msg) > 70:
            commit_msg = commit_msg[:67] + "..."
        
        # Создаем карточку коммита с индикатором наличия LLM анализа
        has_llm = "🤖 " if llm_summary else ""
        
        st.markdown(
            f"""
        <div class="commit-card" style="display: flex; padding: 15px; border-radius: 10px; background-color: {ALFA_GRAY}; margin-bottom: 10px; align-items: center; border-left: 4px solid {type_color};">
            <div style="flex: 0 0 120px; display: flex; flex-direction: column;">
                <div style="font-weight: 500; color: #333;">{commit_date}</div>
                <div style="font-size: 0.8rem; color: #666;">{commit_time}</div>
            </div>
            <div style="flex: 1; font-weight: 500; display: flex; align-items: center;">
                <span style="background-color: {type_color}; color: white; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; margin-right: 10px;">{commit_type}</span>
                {has_llm}{commit_msg}
            </div>
            <div style="flex: 0 0 100px; text-align: right;">
                <a href="{commit_url}" target="_blank" style="text-decoration: none; color: {ALFA_RED}; font-family: monospace; background-color: rgba(239, 49, 36, 0.1); padding: 3px 8px; border-radius: 4px; transition: all 0.2s ease;">{commit_sha}</a>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        
        # Если есть LLM анализ, показываем его в экспандере с улучшенным форматированием
        if llm_summary:
            with st.expander("🤖 View AI Analysis"):
                # Добавляем заголовок отдельно
                st.markdown("## AI Code Analysis")
                
                # Отображаем анализ LLM как обычный Markdown
                st.markdown(llm_summary)
        
        # Добавляем разделитель для лучшей читаемости
        if i < len(recent_commits) - 1:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
    
    # Добавляем футер с информацией и кнопками
    st.markdown(
        """
    <div style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #E5E5E5; text-align: center;">
        <div style="font-size: 0.9rem; color: #666; margin-bottom: 1rem;">
            Enhanced visualization with interactive charts
        </div>
        <div style="display: flex; justify-content: center; gap: 1rem;">
            <div style="background-color: #F5F5F5; padding: 0.7rem 1.2rem; border-radius: 30px; font-weight: 500; color: #333; font-size: 0.9rem;">
                <span style="margin-right: 5px;">📊</span> Analytics Dashboard
            </div>
            <div style="background-color: #F5F5F5; padding: 0.7rem 1.2rem; border-radius: 30px; font-weight: 500; color: #333; font-size: 0.9rem;">
                <span style="margin-right: 5px;">🔍</span> Advanced Insights
            </div>
            <div style="background-color: #F5F5F5; padding: 0.7rem 1.2rem; border-radius: 30px; font-weight: 500; color: #333; font-size: 0.9rem;">
                <span style="margin-right: 5px;">🚀</span> Performance Metrics
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )