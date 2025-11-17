from pandas import read_json, DataFrame
from dotenv import load_dotenv
from os.path import join, dirname
from os import getenv
from openai import OpenAI


load_dotenv(".env")

OPENAI_API_KEY = getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)



def get_embedding(text):
    resp = client.embeddings.create(model="text-embedding-3-large", input=text)
    return resp.data[0].embedding

def main(month: int, year: int, file_name: str):
    meeting_notes = read_json(file_name)
    output = []
    for index, row in meeting_notes.iterrows():
        for point in row['points']:
            embedding = get_embedding(point)

            output.append({
                'year': year,
                'month': month,
                'slide': row['slide'],
                'point': point,
                'embedding': embedding
            })

    return output

# Main execution
if __name__ == "__main__":
    year = 2025
    month = 9

    meeting_notes_file = "2025-09-meeting.json"
    output_file_name = f"{year}-{month}-meeting-embed.json"

    output_file = main(month, year, meeting_notes_file)

    DataFrame(output_file).to_json(output_file_name, orient='records')
