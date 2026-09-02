@echo off
echo جاري تجهيز المكتبات...
pip install -r requirements.txt

echo جاري تجهيز أيقونة البرنامج من لوجو العيادة...
python make_icon.py

echo جاري بناء ملف exe...
pyinstaller --onefile --windowed --name "ClinicApp" --icon "assets\app_icon.ico" --add-data "assets;assets" main.py

echo تم! هتلاقي الملف التنفيذي جوه مجلد dist
pause
