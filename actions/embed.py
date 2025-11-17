from argparse import ArgumentParser
from os import getenv
from os.path import join, dirname

from dotenv import load_dotenv
from openai import OpenAI
from pandas import read_json, DataFrame


load_dotenv(join(dirname(dirname(__file__)), ".env"))

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
    parser = ArgumentParser(description="Embed meeting notes for a specific month/year.")
    parser.add_argument("--year", type=int, required=True, help="Year of the meeting notes (e.g. 2025).")
    parser.add_argument("--month", type=int, required=True, help="Month of the meeting notes as a number (e.g. 9).")
    parser.add_argument("--notes-file", required=True, help="Path to the meeting notes JSON file.")
    parser.add_argument("--output-file", help="Optional path for the output JSON file.")
    args = parser.parse_args()

    year = args.year
    month = args.month
    meeting_notes_file = args.notes_file
    output_file_name = args.output_file or f"{year}-{month}-meeting-embed.json"

    output_file = main(month, year, meeting_notes_file)

    DataFrame(output_file).to_json(join('embeddings', output_file_name), orient='records')
