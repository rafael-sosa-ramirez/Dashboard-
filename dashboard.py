# dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Business Intelligence",
    layout="wide",
    page_icon="🚀"
)

# --- FUNCIÓN DE CARGA Y PREPROCESAMIENTO DE DATOS ---
@st.cache_data
def load_and_process_data(file_path):
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date_id'].str.replace('D', ''), format='%Y%m%d')
    df['month'] = df['date'].dt.to_period('M')
    channel_mapping = {'CH1': 'Web', 'CH2': 'App', 'CH3': 'Teléfono', 'CH4': 'Partner'}
    df['channel_name'] = df['channel_id'].map(channel_mapping).fillna('Otro')
    return df

# --- FUNCIÓN PARA ANÁLISIS DE RETENCIÓN (COHORTS) ---
@st.cache_data
def calculate_retention(df):
    df_retention = df.copy()
    df_retention['acquisition_month'] = df_retention.groupby('customer_id')['month'].transform('min')
    acq_month_int = df_retention['acquisition_month'].dt.year * 12 + df_retention['acquisition_month'].dt.month
    current_month_int = df_retention['month'].dt.year * 12 + df_retention['month'].dt.month
    df_retention['cohort_index'] = current_month_int - acq_month_int
    cohort_data = df_retention.groupby(['acquisition_month', 'cohort_index'])['customer_id'].nunique().reset_index()
    cohort_counts = cohort_data.pivot_table(index='acquisition_month', columns='cohort_index', values='customer_id')
    cohort_sizes = cohort_counts.iloc[:, 0]
    retention_matrix = cohort_counts.divide(cohort_sizes, axis=0) * 100
    return retention_matrix

# --- EJECUCIÓN PRINCIPAL ---
file_name = "Synthetic reserves dataset.csv"
try:
    df_base = load_and_process_data(file_name)
except FileNotFoundError:
    st.error(f"Error: El archivo '{file_name}' no se encontró. Asegúrate de que está en la misma carpeta que dashboard.py.")
    st.stop()

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("📊 Revenue Analytics & Customer Intelligence Hub")
st.markdown("### *Advanced Business Intelligence Dashboard for Restaurant SaaS Platform*")
st.markdown("---")

# --- BARRA LATERAL CON FILTROS ---
st.sidebar.header("Filtros Interactivos")
min_date = df_base['date'].min().date()
max_date = df_base['date'].max().date()
selected_date_range = st.sidebar.date_input('Selecciona Rango de Fechas', value=(min_date, max_date), min_value=min_date, max_value=max_date)
all_restaurants = sorted(df_base['restaurant_id'].unique())
selected_restaurants = st.sidebar.multiselect('Selecciona Restaurante(s)', options=all_restaurants, default=all_restaurants)
all_channels = sorted(df_base['channel_name'].unique())
selected_channels = st.sidebar.multiselect('Selecciona Canal(es) de Reserva', options=all_channels, default=all_channels)

# --- FILTRADO DEL DATAFRAME ---
start_date, end_date = pd.to_datetime(selected_date_range[0]), pd.to_datetime(selected_date_range[1])
df_filtered = df_base[(df_base['date'] >= start_date) & (df_base['date'] <= end_date) & (df_base['restaurant_id'].isin(selected_restaurants)) & (df_base['channel_name'].isin(selected_channels))]
st.sidebar.metric(label="Total Reservas (Bruto)", value=f"{len(df_filtered)}")

# --- CUERPO PRINCIPAL DEL DASHBOARD ---
if df_filtered.empty:
    st.warning("No hay datos disponibles para los filtros seleccionados.")
else:
    st.header("🎯 Executive KPIs & Performance Metrics")
    total_reservations_bruto = len(df_filtered)
    df_confirmadas = df_filtered[df_filtered['status'] == 'Confirmada']
    
    total_revenue = df_confirmadas['total_spent'].sum()
    avg_ticket = df_confirmadas['total_spent'].mean() if not df_confirmadas.empty else 0
    confirmation_rate = len(df_confirmadas) / total_reservations_bruto * 100 if total_reservations_bruto > 0 else 0
    cancellation_rate = (df_filtered['status'] == 'Cancelada').sum() / total_reservations_bruto * 100
    no_show_rate = (df_filtered['status'] == 'No Show').sum() / total_reservations_bruto * 100

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Ingresos Totales", f"€ {total_revenue:,.2f}")
    kpi2.metric("Ticket Promedio", f"€ {avg_ticket:,.2f}")
    kpi3.metric("Tasa de Confirmación", f"{confirmation_rate:.1f}%")
    kpi4.metric("Tasa de Cancelación", f"{cancellation_rate:.1f}%", delta_color="inverse")
    kpi5.metric("Tasa de No-Show", f"{no_show_rate:.1f}%", delta_color="inverse")
    
    st.markdown("---")

    # --- SECCIÓN 1: TABLA DE RENDIMIENTO POR RESTAURANTE ---
    st.header("🏪 Restaurant Performance Intelligence")
    
    if df_confirmadas.empty:
        st.info("No hay reservas 'Confirmadas' en la selección actual para mostrar el análisis detallado.")
    else:
        restaurant_revenue = df_confirmadas.groupby('restaurant_id').agg(Ingresos_Totales=('total_spent', 'sum'), Ticket_Promedio=('total_spent', 'mean'))
        status_counts = df_filtered.groupby('restaurant_id')['status'].value_counts().unstack(fill_value=0)
        restaurant_summary = pd.concat([restaurant_revenue, status_counts], axis=1).fillna(0)
        restaurant_summary['Total_Reservas'] = restaurant_summary[['Confirmada', 'Cancelada', 'No Show']].sum(axis=1)
        restaurant_summary['Tasa_Cancelacion_%'] = (restaurant_summary['Cancelada'] / restaurant_summary['Total_Reservas'] * 100).round(1)
        restaurant_summary['Tasa_NoShow_%'] = (restaurant_summary['No Show'] / restaurant_summary['Total_Reservas'] * 100).round(1)

        display_cols = ['Ingresos_Totales', 'Ticket_Promedio', 'Confirmada', 'Tasa_Cancelacion_%', 'Tasa_NoShow_%']
        st.dataframe(restaurant_summary[display_cols].sort_values('Ingresos_Totales', ascending=False),
            column_config={ "Ingresos_Totales": st.column_config.NumberColumn(format="€ %.2f"), "Ticket_Promedio": st.column_config.NumberColumn(format="€ %.2f"),
                "Tasa_Cancelacion_%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Tasa_NoShow_%": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            }, use_container_width=True)

        st.markdown("---")

        st.header("📈 Revenue Trends & Channel Analytics")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Ingresos Semanales por Restaurante")
            weekly_revenue = df_confirmadas.groupby(['restaurant_id', pd.Grouper(key='date', freq='W-Mon')])['total_spent'].sum().reset_index()
            fig_weekly = px.line(weekly_revenue, x='date', y='total_spent', color='restaurant_id', markers=True, labels={'date': 'Semana', 'total_spent': 'Ingresos (€)'})
            st.plotly_chart(fig_weekly, use_container_width=True)
        with col2:
            st.subheader("Distribución de Reservas por Canal")
            fig_channel = px.pie(df_confirmadas, names='channel_name', hole=0.4)
            st.plotly_chart(fig_channel, use_container_width=True)

        # --- NUEVA SECCIÓN: BOXPLOT DE GASTO ---
        st.markdown("---")
        st.header("💎 Revenue Distribution & High-Value Customer Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Revenue Distribution Analysis")
            fig_boxplot = px.box(
                df_confirmadas, 
                y='total_spent',
                title='Customer Spending Pattern Analysis',
                labels={'total_spent': 'Revenue per Booking (€)'}
            )
            fig_boxplot.update_layout(showlegend=False)
            st.plotly_chart(fig_boxplot, use_container_width=True)
            
            # Estadísticas descriptivas
            stats = df_confirmadas['total_spent'].describe()
            st.subheader("🎯 Revenue Insights")
            col_stats1, col_stats2 = st.columns(2)
            with col_stats1:
                st.metric("Median Revenue", f"€ {stats['50%']:.2f}")
                st.metric("25th Percentile", f"€ {stats['25%']:.2f}")
            with col_stats2:
                st.metric("75th Percentile", f"€ {stats['75%']:.2f}")
                st.metric("Peak Revenue", f"€ {stats['max']:.2f}")
        
        with col2:
            st.subheader("Restaurant Revenue Benchmarking")
            fig_boxplot_restaurant = px.box(
                df_confirmadas, 
                x='restaurant_id',
                y='total_spent',
                title='Revenue Performance by Location',
                labels={'total_spent': 'Revenue (€)', 'restaurant_id': 'Restaurant ID'}
            )
            st.plotly_chart(fig_boxplot_restaurant, use_container_width=True)
            
            # Top outliers (valores atípicos)
            q3 = df_confirmadas['total_spent'].quantile(0.75)
            iqr = q3 - df_confirmadas['total_spent'].quantile(0.25)
            upper_bound = q3 + 1.5 * iqr
            outliers = df_confirmadas[df_confirmadas['total_spent'] > upper_bound]
            
            if not outliers.empty:
                st.subheader("🌟 Premium Customer Bookings")
                st.write(f"High-value bookings > €{upper_bound:.2f}")
                st.dataframe(
                    outliers[['restaurant_id', 'total_spent', 'channel_name']].sort_values('total_spent', ascending=False).head(),
                    use_container_width=True
                )
            else:
                st.info("No premium bookings detected in current selection")
            
        st.markdown("---")

        # --- SECCIÓN 3: ANÁLISIS DE CHURN Y RETENCIÓN ---
        st.header("🔄 Customer Retention Intelligence & Churn Analysis")
        retention_matrix = calculate_retention(df_confirmadas)
        
        if retention_matrix.shape[1] < 2:
            st.info("💡 Se necesita un rango de fechas de varios meses para calcular y visualizar la tasa de retención de cl)
