import json
import pandas as pd
from db import Database

df = pd.read_csv("C:/Users/ocean/Downloads/Physical_Cleaned_Symptom_Curation_Round_3 - Sheet26.csv")
# symptoms = list(set(df["symptoms"].tolist()))
other = df["other_symptoms"].dropna().apply(lambda x: str(x).strip()).tolist()
nlu = df["nlu"].dropna().apply(lambda x: str(x).replace("[", ""))
nlu = nlu.apply(lambda x: x.replace("]", ""))
nlu = nlu.apply(lambda x: x.strip())
nlu = nlu.apply(lambda x: x.replace("(symptom)", ""))
nlu = nlu.apply(lambda x: x.replace("-", ""))
nlu = nlu.apply(lambda x: x.strip())
nlu = nlu.tolist()
new = []

symptoms = ["increasing confusion", "confusion in the evening hours", "confusion and behavior changes",
            "sudden confusion", "confusion", "tenderness in abdomen", "breast tenderness", "tenderness in scrotum",
            "tenderness in joint", "tenderness in the affected area", "tenderness on skin",
            "pain, tenderness or weakness, often around ankle, foot, wrist, thumb, knee, leg or back",
            "abnormal vaginal bleeding especially during or after sex", "abnormal vaginal bleeding",
            "bleeding", "slight bleeding if the lesions are rubbed or scraped", "bleeding easily",
            "bleeding from anus", "bleeding gums", "bleeding after intercourse",
            "bleeding between menstrual periods", "bleeding from scratched skin",
            "bleeding from your nose without any injury", "heavy bleeding during menstrual period",
            "memory loss of recent events", "memory loss", "loss of ability to do everyday tasks",
            "problems with recognition", "problems with spatial awareness", "cognitive deficits",
            "apathy and withdrawal", "personality or behaviour changes",
            "problems with speaking reading or writing", "tenderness",
            "itching",
            "itching in one or both eyes",
            "itching along the insides of the wrists",
            "itching around the belly button",
            "itching around the genitals",
            "itching around the nipples",
            "itching around the waist",
            "itching between the fingers and toes",
            "itching in the armpits",
            "itching in the groin area",
            "itching in vagina",
            "itching on the buttocks",
            "itching on the chest",
            "itching on the inner elbows",
            "itching on the soles of the feet",
            "itching worse at night",
            "itching in nose",
            "itching in eyes",
            "itching in throat",
            "itching in anus",
            "itching and irritation or fissure around the vagina",
            "itching between toes",
            "itching and irritation in and around the ear"
            ]
exclude = ["neck pain", "pain", "chest pain worsened by coughing", "chest pain when you cough",
           "headache and neck pain that lasts 3 days or longer"
           "shortness of breath or chest pain or palpitation worsen when lying down",
           "swelling in the face hands or legs",
           "intense joint pain usually at big toe",
           "intermittent back pain that may radiate to the extremities"]
# symptoms = df["symptoms"].dropna().tolist()
# symptoms = list(set(symptoms))

# db = Database("medai")
# db_symptoms = db.get_all_symptoms_name()

f = open('../data_files/symptoms.json')
symptom_data = json.load(f)
print(symptom_data)
for i in other:
    if i not in symptoms and i not in symptom_data["physical_symptoms"]["other_symptoms"]:
        symptom_data["physical_symptoms"]["other_symptoms"].append(i)
with open("sample.json", "w") as out:
    json.dump(symptom_data, out, indent=4)
