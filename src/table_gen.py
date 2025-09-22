import os
import psycopg2

class Table_gen:
    @staticmethod
    def table_generator(generated_files, video_bytes_list, audio_bytes_list=None):

        base_path = generated_files[1]
        topic_name = os.path.basename(base_path)

        py_files = generated_files[0].get("py_files", [])

        if len(video_bytes_list) != len(py_files):
            print("Warning: number of video bytes and txt files do not match!")

        try:
            conn = psycopg2.connect(
                dbname="airlines_flights_data",
                user="vivek",
                password="8811",
                host="localhost",
                port="5432"
            )
            cur = conn.cursor()

            # Create table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Test_table (
                    topic TEXT,
                    script TEXT,
                    blob BYTEA,
                    remark TEXT
                )
            """)

            for i, py_file in enumerate(txt_files):
                script_name = os.path.splitext(os.path.basename(py_file))[0]

                video_bytes = video_bytes_list[i] if i < len(video_bytes_list) else None

                if video_bytes is None:
                    print(f"Skipping {script_name}, no video bytes available")
                    continue

                cur.execute("""
                    INSERT INTO Test_table (topic, script, blob, remark)
                    VALUES (%s, %s, %s, %s)
                """, (topic_name, script_name, video_bytes, ""))

                print(f"Inserted {script_name} for topic {topic_name} with video bytes")

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print("Database error:", e)
