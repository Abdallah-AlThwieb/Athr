# استخدم إصدار Python 3.10
FROM python:3.10-slim

# إعداد مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ الملفات إلى الحاوية
COPY . .

# تثبيت المتطلبات
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# الأمر الذي يتم تشغيله عند الإقلاع
CMD ["gunicorn", "app:app"]
