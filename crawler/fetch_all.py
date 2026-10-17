import subprocess

files = [
    "crawler/fetch_academic_calendar.py",
    "crawler/fetch_health_insurance.py",
    "crawler/fetch_international_students.py",
    "crawler/fetch_parking.py",
    "crawler/fetch_tuition.py"
]

for file in files:
    print(f"\nRunning {file}...")
    subprocess.run(["python3", file])

print("\nAll crawlers finished!")