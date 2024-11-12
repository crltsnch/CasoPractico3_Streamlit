import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from statsmodels.tsa.seasonal import seasonal_decompose
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.models import load_model

# Cargar los datos desde el archivo CSV
file_path = "IBEX/data/ibex_data_clean.csv"
df = pd.read_csv(file_path)

# Mostrar las primeras filas del DataFrame en Streamlit
st.write("Datos del IBEX35 desde el 2012 hasta la actualidad")
st.write(df.head())

# Convertir la columna 'Date' a tipo datetime y establecerla como índice
df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
df.set_index('Date', inplace=True)

# Filtrar todas las filas donde 'Close' no sea nulo o NaN
df_filtered = df.dropna(subset=['Close'])

# Seleccionar la columna objetivo
data = df_filtered[['Close']]

'''# Descomposición de la serie temporal
decomposition = seasonal_decompose(df_filtered['Close'], model='additive', period=365)

# Obtención de las componentes
trend = decomposition.trend
seasonal = decomposition.seasonal
residuals = decomposition.resid

# Graficar las componentes de la descomposición de la serie temporal
st.write('### Descomposición de la Serie Temporal')
fig1, ax1 = plt.subplots(figsize=(12, 8))

plt.subplot(411)
plt.plot(df_filtered['Close'], label='Original', color='blue')
plt.legend()
plt.title('Serie Temporal Original')

plt.subplot(412)
plt.plot(trend, label='Tendencia', color='red')
plt.legend()
plt.title('Tendencia')

plt.subplot(413)
plt.plot(seasonal, label='Estacionalidad', color='green')
plt.legend()
plt.title('Estacionalidad')

plt.subplot(414)
plt.plot(residuals, label='Residuos', color='orange')
plt.legend()
plt.title('Residuos')

plt.tight_layout()
st.pyplot(fig1)'''

# Escalar los datos entre 0 y 1
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data)

# Crear secuencias de datos para entrenamiento
def create_sequences(data, seq_length):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length])
    return np.array(X), np.array(y)

# Definir la longitud de la secuencia
seq_length = 365
X, y = create_sequences(scaled_data, seq_length)

# Dividir los datos en entrenamiento y prueba (80% - 20%)
train_size = int(len(X) * 0.8)
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Construir el modelo LSTM
model = Sequential()
model.add(LSTM(128, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])))
model.add(LSTM(64))
model.add(Dense(1))

# Compilar el modelo
model.compile(optimizer='adam', loss='mean_squared_error')

# Entrenar el modelo
model.fit(X_train, y_train, epochs=10, batch_size=32, validation_data=(X_test, y_test))

# Evaluar el modelo
loss = model.evaluate(X_test, y_test)
st.write(f"Test Loss: {loss}")

# Hacer predicciones con el modelo LSTM
predicted_prices = model.predict(X_test)

# Función para calcular métricas de evaluación
def calcular_metricas(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    return mse, mae, rmse, r2

# Calcular las métricas para el conjunto de prueba
lstm_metrics = calcular_metricas(y_test, predicted_prices)

# Mostrar las métricas en Streamlit
st.write("Métricas del Modelo LSTM:")
st.write(f"MSE: {lstm_metrics[0]}, MAE: {lstm_metrics[1]}, RMSE: {lstm_metrics[2]}, R²: {lstm_metrics[3]}")

# Escalado inverso
predicted_prices_unscaled = scaler.inverse_transform(predicted_prices.reshape(-1, 1))
y_test_unscaled = scaler.inverse_transform(y_test.reshape(-1, 1))



# Calcular intervalo de confianza del 70%
z_value = 1.04  # Valor crítico para un intervalo de confianza del 70%
confidence_interval = z_value * np.std(y_test_unscaled - predicted_prices_unscaled)

# Crear los intervalos superior e inferior
upper_bound = predicted_prices_unscaled + confidence_interval
lower_bound = predicted_prices_unscaled - confidence_interval

# Extraer las fechas para el conjunto de prueba
test_dates = df_filtered.index[-len(y_test_unscaled):]

# Graficar los resultados con los intervalos de confianza en Streamlit
st.write('### Predicciones LSTM con Intervalo de Confianza del 70%')
fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(test_dates, y_test_unscaled, label='Valores Reales', color='blue')
ax.plot(test_dates, predicted_prices_unscaled, label=f'Predicciones LSTM - RMSE: {lstm_metrics[2]:.2f}', linestyle='--', color='red')
ax.fill_between(test_dates, lower_bound.flatten(), upper_bound.flatten(), color='gray', alpha=0.3, label='Intervalo de Confianza (70%)')
ax.set_xlabel('Fecha')
ax.set_ylabel('Precio de Cierre')
ax.set_title('Predicciones del Modelo LSTM con Intervalo de Confianza del 70%')
ax.legend()
st.pyplot(fig)





# Graficar los residuos en Streamlit
lstm_residuals = y_test_unscaled - predicted_prices_unscaled
st.write('### Residuos del Modelo LSTM')
fig2, ax2 = plt.subplots(figsize=(12, 6))
ax2.plot(lstm_residuals, label='LSTM Residuos', color='red')
ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
ax2.set_xlabel('Días')
ax2.set_ylabel('Residuos')
ax2.set_title('Residuos del Modelo LSTM')
ax2.legend()
st.pyplot(fig2)

# Graficar histograma de los residuos en Streamlit
st.write('### Histograma de Residuos del Modelo LSTM')
fig3, ax3 = plt.subplots(figsize=(12, 6))
ax3.hist(lstm_residuals, bins=20, color='red', alpha=0.5, label='LSTM Residuos')
ax3.set_xlabel('Residuos')
ax3.set_ylabel('Frecuencia')
ax3.set_title('Histograma de Residuos del Modelo LSTM')
ax3.legend()
ax3.grid(True)
st.pyplot(fig3)




# Crear un DataFrame para los residuos
residuals_df = pd.DataFrame({
    'Día': np.arange(len(y_test_unscaled)),
    'LSTM Residuos': lstm_residuals.flatten()
})

# Mostrar la tabla de resultados de residuos en Streamlit
st.write('### Tabla de Residuos del Modelo LSTM')
st.write(residuals_df)

# Calcular y mostrar el coeficiente R² en entrenamiento
train_predictions = model.predict(X_train)
train_predictions_unscaled = scaler.inverse_transform(train_predictions)
r2_train = r2_score(scaler.inverse_transform(y_train), train_predictions_unscaled)
st.write(f'Coeficiente de determinación R² en entrenamiento: {r2_train:.2f}')
st.write(f'Coeficiente de determinación R² en prueba: {lstm_metrics[3]:.2f}')

# Guardar modelo
save_path = "IBEX/resultados/modelo_lstm_ibex.keras"
model.save(save_path)