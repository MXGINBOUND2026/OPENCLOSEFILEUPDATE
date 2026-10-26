import io
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="POD Categorizer & Merger", page_icon="📦", layout="centered"
)

st.title("📦 Aplikasi Pemisah & Penggabung POD")
st.markdown(
    "Unggah file **CSV Baru** dan file **CLOSE Lama (~500MB)** untuk memproses"
    " kategori OPEN/CLOSE secara otomatis."
)

# Widget Upload File
uploaded_new_file = st.file_uploader(
    "1. Pilih / Upload File CSV Baru", type=["csv"]
)
uploaded_old_file = st.file_uploader(
    "2. Pilih / Upload File CLOSE Lama (~500MB) [Opsional]", type=["csv"]
)

if st.button("🚀 PROSES SEKARANG", type="primary", use_container_width=True):
  if uploaded_new_file is None:
    st.warning("⚠️ Harap upload file CSV baru terlebih dahulu!")
  else:
    with st.spinner("Sedang memproses data, mohon tunggu..."):
      try:
        # 1. Baca File Baru
        df_new = pd.read_csv(uploaded_new_file, low_memory=False)

        # Aturan 1
        cond1 = (df_new['STATUS_POD'].astype(str).str.strip() == 'Return Shipper') & (
            df_new['WUS_REMARKS']
            .astype(str)
            .str.contains('HRS|HRI', case=False, na=False)
        )

        # Aturan 2
        bilnote_series = df_new['BILNOTE_AMOUNT'].astype(str).str.strip()
        cond2 = (
            df_new['BILNOTE_AMOUNT'].notna()
            & (bilnote_series != '')
            & (bilnote_series.str.lower() != 'nan')
            & (df_new['STATUS_POD'].astype(str).str.strip() == 'Success')
            & (
                df_new['SCO_NO']
                .astype(str)
                .str.contains('SCO', case=False, na=False)
            )
        )

        # Aturan 3
        cond3 = (df_new['STATUS_POD'].astype(str).str.strip() == 'Success') & (
            df_new['WUS_REMARKS']
            .astype(str)
            .str.contains('HRS', case=False, na=False)
        )

        close_mask = cond1 | cond2 | cond3

        df_new_close = df_new[close_mask].copy()
        df_new_open = df_new[~close_mask].copy()

        # 2. Proses File CLOSE Lama & Deduplikasi jika ada
        if uploaded_old_file is not None:
          df_old_close = pd.read_csv(uploaded_old_file, low_memory=False)
          df_combined_close = pd.concat(
              [df_old_close, df_new_close], ignore_index=True
          )
        else:
          df_combined_close = df_new_close

        if (
            'AWB' in df_combined_close.columns
            and 'TGL_TARIK_REPORT' in df_combined_close.columns
        ):
          df_combined_close['TGL_TARIK_REPORT_DT'] = pd.to_datetime(
              df_combined_close['TGL_TARIK_REPORT'], errors='coerce'
          )
          df_combined_close = df_combined_close.sort_values(
              by='TGL_TARIK_REPORT_DT', ascending=False
          )
          df_combined_close = df_combined_close.drop_duplicates(
              subset=['AWB'], keep='first'
          )
          df_combined_close = df_combined_close.drop(
              columns=['TGL_TARIK_REPORT_DT']
          )

        st.success("🎉 Proses Berhasil Dilakukan!")

        # Tombol Download Hasil
        col1, col2 = st.columns(2)

        with col1:
          st.subheader("File OPEN Baru")
          st.write(f"Jumlah baris: {len(df_new_open):,}")
          st.download_button(
              label="📥 Download hasil_open_baru.csv",
              data=df_new_open.to_csv(index=False).encode('utf-8'),
              file_name="hasil_open_baru.csv",
              mime="text/csv",
          )

        with col2:
          st.subheader("File CLOSE Final")
          st.write(f"Jumlah baris: {len(df_combined_close):,}")
          st.download_button(
              label="📥 Download hasil_close_final.csv",
              data=df_combined_close.to_csv(index=False).encode('utf-8'),
              file_name="hasil_close_final.csv",
              mime="text/csv",
          )

      except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses data: {e}")
