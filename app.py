import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests


# описательная статистика
def describe_city_data(data, city):
    city_data = data.xs(city, level='city')
    return city_data.describe()


# временные ряды и аномалии
def visualize_city_temperature(data, city, start_date: str = None, end_date: str = None):
    city_data = data.xs(city, level='city')

    if start_date:
        city_data = city_data[city_data.index >= pd.to_datetime(start_date)]
    if end_date:
        city_data = city_data[city_data.index <= pd.to_datetime(end_date)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=city_data.index, y=city_data['temperature'],
                             mode='lines', name='Temperature', line=dict(color='grey')))
    fig.add_trace(go.Scatter(x=city_data.index, y=city_data['rolling_mean_temperature'],
                             mode='lines', name='Rolling Mean (30 days)', line=dict(color='yellow')))
    fig.add_trace(go.Scatter(x=city_data.index, y=city_data['long_term_trend'],
                             mode='lines', name='Long-term Trend (365 days)', line=dict(color='black')))

    anomalies = city_data[city_data['anomaly']]
    fig.add_trace(go.Scatter(x=anomalies.index, y=anomalies['temperature'],
                             mode='markers', name='Anomalies', marker=dict(color='red', size=8)))

    fig.update_layout(title=f'Temperature Trends and Anomalies in {city}',
                      xaxis_title='Date', yaxis_title='Temperature', hovermode='x unified')
    st.plotly_chart(fig)


# проверка температуры через API
def get_current_temperature(city, country_code, api_key):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city},{country_code}&APPID={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['main']['temp']
    elif response.status_code == 401:
        st.error("Ошибка: Invalid API key. Проверьте введенный ключ.")
    else:
        st.error(f"Ошибка: {response.status_code}")
    return None


def check_temperature_normality(data, city, current_temperature):
    city_data = data.xs(city, level='city')
    rolling_mean = city_data['rolling_mean_temperature'].iloc[-1]
    rolling_std = city_data['rolling_std_temperature'].iloc[-1]
    lower_bound = rolling_mean - 2 * rolling_std
    upper_bound = rolling_mean + 2 * rolling_std

    if current_temperature < lower_bound:
        return "Температура ниже нормы (аномалия)"
    elif current_temperature > upper_bound:
        return "Температура выше нормы (аномалия)"
    else:
        return "Температура в пределах нормы"


# Интерфейс Streamlit

st.title("Мониторинг и анализ погоды")

# загрузка данных
st.sidebar.header("Загрузка данных")
uploaded_file = st.sidebar.file_uploader("Загрузите CSV-файл с историческими данными", type=['csv'])

if uploaded_file:
    data = pd.read_csv(uploaded_file, parse_dates=['timestamp'])
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.set_index(['city', 'timestamp'])

    # скользящее среднее и аномалии
    data['rolling_mean_temperature'] = data.groupby('city')['temperature'].rolling(window=30).mean().reset_index(
        level=0, drop=True)
    data['rolling_std_temperature'] = data.groupby('city')['temperature'].rolling(window=30).std().reset_index(level=0,
                                                                                                               drop=True)
    data['anomaly'] = (
                (data['temperature'] > (data['rolling_mean_temperature'] + 2 * data['rolling_std_temperature'])) |
                (data['temperature'] < (data['rolling_mean_temperature'] - 2 * data['rolling_std_temperature'])))
    data['long_term_trend'] = data.groupby('city')['temperature'].rolling(window=365).mean().reset_index(level=0,
                                                                                                         drop=True)

    # выбор города
    st.sidebar.header("Выбор города")
    city = st.sidebar.selectbox("Выберите город", data.index.get_level_values('city').unique())

    # описательная статистика
    st.header(f"Описательная статистика для {city}")
    st.write(describe_city_data(data, city))

    # визуализация
    st.sidebar.text("Укажите временной диапазон (опционально)")
    start_date = st.sidebar.text_input("Введите дату начала отсчета \n(например,  2001-01-01)", None)
    end_date = st.sidebar.text_input("Введите дату конца отсчета \n(например,  2001-01-01)", None)
    st.header(f"Временной ряд температур для {city}")
    visualize_city_temperature(data, city, start_date, end_date)

    # API OpenWeatherMap
    st.sidebar.header("API OpenWeatherMap")
    api_key = st.sidebar.text_input("Введите API-ключ OpenWeatherMap", type="password")
    country_code = st.sidebar.text_input("Введите код страны (опционально)", "usa")

    if api_key:
        st.header(f"Текущая температура в {city}")
        current_temp = get_current_temperature(city, country_code, api_key)
        if current_temp is not None:
            st.write(f"**Текущая температура:** {current_temp}°C")
            status = check_temperature_normality(data, city, current_temp)
            st.write(f"**Статус:** {status}")
else:
    st.info("Пожалуйста, загрузите данные для продолжения.")
