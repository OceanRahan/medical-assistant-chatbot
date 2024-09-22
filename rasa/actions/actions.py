# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


import json
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet, AllSlotsReset, Restarted
from utils.db import Database
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

user_symptom_count = {}


def initiate_count(sender_id):
    if sender_id not in user_symptom_count:
        user_symptom_count.update({
            sender_id:
                {
                    "mental_symptom_count": 0,
                    "physical_symptom_count": 0,
                    "common_symptom_count": 0,
                    "free_text": [],
                    "symptoms": [],
                    "already_asked": []

                }})


def symptom_count(intent, sender_id, msg):
    initiate_count(sender_id)
    mental_health_intents = ["depression", "anxiety", "personality_disorder", "bipolar_disorder", "psychosis",
                             "schizophrenia", "dementia"]
    physical_health_intents = ["pain", "cough", "swelling", "headache", "fever", "other_symptoms"]
    print("here in symptom count", intent)
    if intent in mental_health_intents:
        user_symptom_count[sender_id].update({
            "mental_symptom_count": user_symptom_count[sender_id]["mental_symptom_count"] + 1,
        })
    elif intent in physical_health_intents:
        user_symptom_count[sender_id].update({
            "physical_symptom_count": user_symptom_count[sender_id]["physical_symptom_count"] + 1,
        })
    elif intent == "common":
        user_symptom_count[sender_id].update({
            "common_symptom_count": user_symptom_count[sender_id]["common_symptom_count"] + 1,
        })
    if "/" in msg:
        msg = msg.replace("/", "").strip()
        user_symptom_count[sender_id]["symptoms"].append(msg)
    else:
        user_symptom_count[sender_id]["free_text"].append(msg)
    print(user_symptom_count)


def get_filtered_suggestion(symptom, parent, sorted_symptom):
    """

    It takes a list of symptoms that has been entered by a user and returns top ten symptom suggestion based on
    symptom-symptom correlation. Called from **all_user.symptom_checker_views.SymptomsSuggestions** module.

    Parameters
    _____________
    symptom_list: list

    Returns
    _____________
    top ten correlated symptoms: list
    """
    unique = []
    taken = []
    special_rule = ["pain", "cough", "fever", "wheezing", "discomfort", "swelling", "redness", "tenderness",
                    "headache", "confusion", "numbness", "phlegm", "itching", "ache"]
    if parent != symptom and parent != "" and parent not in taken:
        taken.append(parent)
    for k in special_rule:
        if k in symptom:
            if k == "pain":
                if "ache" not in taken:
                    taken.append("ache")
            if k not in taken:
                taken.append(k)
    for i in sorted_symptom:
        if i not in taken:
            unique.append(i)
    unique = unique
    return unique, taken


def get_random_suggestion(symptom_type, sender_id, msg):
    f = open('data_files/symptoms_sorted.json')
    symptom_data = json.load(f)[symptom_type]
    keys = ["pain", "cough", "fever", "swelling", "confusion", "tenderness", "bleeding",
            "itching", "headache"]
    key_found = False
    if symptom_type == "physical_symptoms":
        for key in keys:
            if key in msg:
                symptom_data = symptom_data[key]
                key_found = True
                break
        if not key_found:
            symptom_data = symptom_data["other_symptoms"]
    for i in user_symptom_count[sender_id]["already_asked"]:
        if i in symptom_data:
            symptom_data.remove(i)
    for i in user_symptom_count[sender_id]["free_text"]:
        if i in symptom_data:
            symptom_data.remove(i)
    if len(symptom_data) < 2:
        symptom_data = symptom_data + list(set(user_symptom_count[sender_id]["already_asked"])
                                           - set(user_symptom_count[sender_id]["symptoms"]))
    if len(symptom_data) < 5:
        unique_suggestions = symptom_data[:len(symptom_data)]
    else:
        unique_suggestions = symptom_data[:5]
    print(len(symptom_data))
    return unique_suggestions


def get_relevant_common_suggestions(intent, msg, sender_id):
    mental_health_intents = ["depression", "anxiety", "personality_disorder", "bipolar_disorder", "psychosis",
                             "schizophrenia", "dementia"]
    # physical_health_intents = ["pain", "cough", "swelling", "headache", "fever"]
    initiate_count(sender_id)
    if intent in mental_health_intents:
        unique_suggestions = get_random_suggestion("mental_symptoms", sender_id, msg)
    else:
        if "/" in msg:
            msg = msg.replace("/", "").strip()
        print(msg)
        if msg in user_symptom_count[sender_id]["already_asked"]:
            print("here in db")
            db = Database("medai")
            all_db_symptoms = db.get_all_symptoms_name()
            if msg not in all_db_symptoms:
                msg = db.eng_syn_to_sym(msg)
            parent = db.get_parent_symptom(msg)
            suggestions = list(db.get_correlated_symptoms(msg).keys())[:20]
            for each in user_symptom_count[sender_id]["already_asked"]:
                if each in suggestions:
                    suggestions.remove(each)
            unique_suggestions, taken = get_filtered_suggestion(msg, parent, suggestions)
            user_symptom_count[sender_id]["already_asked"].extend(taken)
            if len(unique_suggestions) < 2:
                unique_suggestions = get_random_suggestion("physical_symptoms", sender_id, msg)
            else:
                if len(unique_suggestions) < 5:
                    unique_suggestions = unique_suggestions[:len(unique_suggestions)]
                else:
                    unique_suggestions = unique_suggestions[:5]
        else:
            unique_suggestions = get_random_suggestion("physical_symptoms", sender_id, msg)

    return unique_suggestions


class ActionCleanupCount(Action):
    def name(self) -> Text:
        return "action_cleanup_count"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        if sender_id in user_symptom_count:
            print("here")
            del user_symptom_count[sender_id]
        return []


class ActionAskSymptom1(Action):
    def name(self) -> Text:
        return "action_ask_symptom1"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        suggestions = get_relevant_common_suggestions(intent, msg, sender_id)
        user_symptom_count[sender_id]["already_asked"].extend(suggestions)
        text = "I see, can you tell me which one of the followings is bothering you the most "
        buttons = []
        for i in suggestions:
            each_dict = {"payload": "/" + i, "title": i}
            buttons.append(each_dict)
        buttons.append({"payload": "/stop", "title": "Finish Now"})
        dispatcher.utter_button_message(text=text, buttons=buttons)

        return []


class ActionAskSymptom2(Action):
    def name(self) -> Text:
        return "action_ask_symptom2"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        suggestions = get_relevant_common_suggestions(intent, msg, sender_id)
        user_symptom_count[sender_id]["already_asked"].extend(suggestions)
        text = "OKay! I get that, don't worry, I am here to help you, " \
               "can you please choose any symptom from below so that I can help you better: "
        buttons = []
        for i in suggestions:
            each_dict = {"payload": "/" + i, "title": i}
            buttons.append(each_dict)
        buttons.append({"payload": "/stop", "title": "Finish Now"})
        dispatcher.utter_button_message(text=text, buttons=buttons)

        return []


class ActionAskSymptom3(Action):
    def name(self) -> Text:
        return "action_ask_symptom3"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        suggestions = get_relevant_common_suggestions(intent, msg, sender_id)
        user_symptom_count[sender_id]["already_asked"].extend(suggestions)
        text = "We are almost there, please choose a symptom from the followings which you are suffering from:"
        buttons = []
        for i in suggestions:
            each_dict = {"payload": "/" + i, "title": i}
            buttons.append(each_dict)
        buttons.append({"payload": "/stop", "title": "Finish Now"})
        dispatcher.utter_button_message(text=text, buttons=buttons)

        return []


class ActionAskSymptom4(Action):
    def name(self) -> Text:
        return "action_ask_symptom4"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        suggestions = get_relevant_common_suggestions(intent, msg, sender_id)
        user_symptom_count[sender_id]["already_asked"].extend(suggestions)
        text = "Alright! Kudos to your patience and bear with me till now, this will be the last question " \
               "before I give you an initial assessment, please choose one:"
        buttons = []
        for i in suggestions:
            each_dict = {"payload": "/" + i, "title": i}
            buttons.append(each_dict)
        buttons.append({"payload": "/stop", "title": "Finish Now"})
        dispatcher.utter_button_message(text=text, buttons=buttons)

        return []


class ValidationActionSymptomCount(FormValidationAction):
    def name(self):
        return "validate_symptom_form"

    def validate_symptom1(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        symptoms = ["pain", "fever", "cough", "swelling", "headache", "weakness", "itching", "bleeding",
                    "tenderness", "confusion"]
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        travel_symptoms_mapping = {
            "live or travelled recently to areas prone to viral "
            "fevers like dengue, malaria, chikungunya or "
            "high prevelance of hepatitis e.g. India or Africa":
            "live or travelled recently to areas prone to viral fevers "
            "like dengue, malaria, chikungunya or high prevelance of hepatitis (e.g. India or Africa)",
            "live or travelled recently to areas prone to diseases "
            "like meningitis e.g. sub-Saharan Africa":
                "live or travelled recently to areas prone to diseases like meningitis (e.g. sub-Saharan Africa)"}
        if msg in travel_symptoms_mapping:
            msg = travel_symptoms_mapping[msg]
            SlotSet("symptom1", msg)
        else:
            for i in symptoms:
                if i in msg:
                    SlotSet("symptom1", msg)
        print(intent)
        print(user_symptom_count)
        symptom_count(intent, sender_id, msg)

        return {}

    def validate_symptom2(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        symptoms = ["pain", "fever", "cough", "swelling", "headache", "weakness", "itching", "bleeding",
                    "tenderness", "confusion"]
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        travel_symptoms_mapping = {
            "live or travelled recently to areas prone to viral "
            "fevers like dengue, malaria, chikungunya or "
            "high prevelance of hepatitis e.g. India or Africa":
                "live or travelled recently to areas prone to viral fevers "
                "like dengue, malaria, chikungunya or high prevelance of hepatitis (e.g. India or Africa)",
            "live or travelled recently to areas prone to diseases "
            "like meningitis e.g. sub-Saharan Africa":
                "live or travelled recently to areas prone to diseases like meningitis (e.g. sub-Saharan Africa)"}
        if msg in travel_symptoms_mapping:
            msg = travel_symptoms_mapping[msg]
            SlotSet("symptom1", msg)
        else:
            for i in symptoms:
                if i in msg:
                    SlotSet("symptom1", msg)
        symptom_count(intent, sender_id, msg)

        return {}

    def validate_symptom3(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        symptoms = ["pain", "fever", "cough", "swelling", "headache", "weakness", "itching", "bleeding",
                    "tenderness", "confusion"]
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        travel_symptoms_mapping = {
            "live or travelled recently to areas prone to viral "
            "fevers like dengue, malaria, chikungunya or "
            "high prevelance of hepatitis e.g. India or Africa":
                "live or travelled recently to areas prone to viral fevers "
                "like dengue, malaria, chikungunya or high prevelance of hepatitis (e.g. India or Africa)",
            "live or travelled recently to areas prone to diseases "
            "like meningitis e.g. sub-Saharan Africa":
                "live or travelled recently to areas prone to diseases like meningitis (e.g. sub-Saharan Africa)"}
        if msg in travel_symptoms_mapping:
            msg = travel_symptoms_mapping[msg]
            SlotSet("symptom1", msg)
        else:
            for i in symptoms:
                if i in msg:
                    SlotSet("symptom1", msg)
        symptom_count(intent, sender_id, msg)

        return {}

    def validate_symptom4(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        symptoms = ["pain", "fever", "cough", "swelling", "headache", "weakness", "itching", "bleeding",
                    "tenderness", "confusion"]
        intent = tracker.get_intent_of_latest_message()
        sender_id = tracker.sender_id
        msg = tracker.current_state()["latest_message"]["text"]
        travel_symptoms_mapping = {
            "live or travelled recently to areas prone to viral "
            "fevers like dengue, malaria, chikungunya or "
            "high prevelance of hepatitis e.g. India or Africa":
                "live or travelled recently to areas prone to viral fevers "
                "like dengue, malaria, chikungunya or high prevelance of hepatitis (e.g. India or Africa)",
            "live or travelled recently to areas prone to diseases "
            "like meningitis e.g. sub-Saharan Africa":
                "live or travelled recently to areas prone to diseases like meningitis (e.g. sub-Saharan Africa)"}
        if msg in travel_symptoms_mapping:
            msg = travel_symptoms_mapping[msg]
            SlotSet("symptom1", msg)
        else:
            for i in symptoms:
                if i in msg:
                    SlotSet("symptom1", msg)
        symptom_count(intent, sender_id, msg)

        return {}


class ActionInitSuggestion(Action):
    def name(self) -> Text:
        return "action_init_suggestion"

    def get_init_suggestion(self):
        return ["pain", "cough", "fever", "swelling", "headache", "depression", "anxiety"]

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = tracker.sender_id
        intent = tracker.get_intent_of_latest_message()
        initiate_count(sender_id)
        suggestions = self.get_init_suggestion()
        user_symptom_count[sender_id]["already_asked"].extend(suggestions)
        buttons = []
        for i in suggestions:
            each_dict = {"payload": "/" + i, "title": i}
            buttons.append(each_dict)
        if intent == "mood_great" or intent == "react_positive" or intent == "init_conversation":
            text = "Please select a symptom below so that I can assist you better:"
        else:
            text = "Please tell me more so that I can help you better, " \
                   "select a symptom that best describes your current ailment:"
        dispatcher.utter_button_message(text=text, buttons=buttons)

        return []


class ActionSymptomCount(Action):
    def name(self) -> Text:
        return "action_symptom_count"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        intent = tracker.get_intent_of_latest_message()
        msg = tracker.current_state()["latest_message"]["text"]
        sender_id = tracker.sender_id
        symptom_count(intent, sender_id, msg)

        return []


class ActionFinal(Action):

    def name(self) -> Text:
        return "action_final"

    def get_verdict(self, mental_symptom_count, physical_symptom_count, common_symptom_count):
        if mental_symptom_count > physical_symptom_count:
            if mental_symptom_count > common_symptom_count:
                verdict = "mental"
                max_count = mental_symptom_count
            elif mental_symptom_count == common_symptom_count:
                verdict = "tie"
                max_count = mental_symptom_count
            else:
                verdict = "common"
                max_count = common_symptom_count
        elif mental_symptom_count == physical_symptom_count:
            if physical_symptom_count == common_symptom_count:
                verdict = "tie"
                max_count = physical_symptom_count
            elif physical_symptom_count > common_symptom_count:
                verdict = "physical"
                max_count = physical_symptom_count
            else:
                verdict = "common"
                max_count = common_symptom_count
        else:
            if physical_symptom_count > common_symptom_count:
                verdict = "physical"
                max_count = physical_symptom_count
            elif physical_symptom_count == common_symptom_count:
                verdict = "tie"
                max_count = physical_symptom_count
            else:
                verdict = "common"
                max_count = common_symptom_count

        return verdict, max_count

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # intent = tracker.get_intent_of_latest_message()
        # msg = tracker.current_state()["latest_message"]["text"]
        sender_id = tracker.sender_id
        if sender_id in user_symptom_count:
            mental_symptom_count = user_symptom_count[sender_id]["mental_symptom_count"]
            physical_symptom_count = user_symptom_count[sender_id]["physical_symptom_count"]
            common_symptom_count = user_symptom_count[sender_id]["common_symptom_count"]
            verdict, max_count = self.get_verdict(mental_symptom_count, physical_symptom_count, common_symptom_count)
            buttons = [{"payload": "/affirm", "title": "Yes"}, {"payload": "/deny", "title": "No"}]
            if max_count < 3:
                dispatcher.utter_button_message(
                    text="Sorry, from your input, I could not detect whether "
                         "you should consult a psychologist or a general physician, would you like to"
                         "explore our expert doctors and book an appointment?", buttons=buttons)
            else:
                if verdict == "mental":
                    dispatcher.utter_message(text="From my initial triaging we would recommend you to consult to a "
                                                  "psychologist or a counselor")
                    dispatcher.utter_button_message(text="We have bunch of expert psychologists and "
                                                         "counselors in our system, "
                                                         "would you like to book an appointment?", buttons=buttons)
                elif verdict == "physical":
                    dispatcher.utter_button_message(text="From my initial triaging we would recommend you to "
                                                         "consult to a physician, "
                                                         "would you like to book an appointment?", buttons=buttons)
                else:
                    dispatcher.utter_button_message(text="Sorry, from your input, I could not detect "
                                                         "whether you should consult a "
                                                         "psychologist or a general physician, would you like to "
                                                         "explore our expert doctors and book an appointment?",
                                                    buttons=buttons)
        else:
            print(sender_id)
            dispatcher.utter_message(text="I am sorry, I am facing some issues, please try again later")
        return [AllSlotsReset(), Restarted()]


class ActionDecision(Action):

    def name(self) -> Text:
        return "action_decision"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        sender_id = tracker.sender_id
        print(user_symptom_count)
        free_text = []
        symptoms = []
        if sender_id in user_symptom_count:
            free_text = user_symptom_count[sender_id]["free_text"]
            symptoms = user_symptom_count[sender_id]["symptoms"]
        for event in tracker.events:
            if (event.get("event") == "bot") and (event.get("event") is not None):
                msg = event.get("text")
                if "explore our expert doctors" in msg:
                    dispatcher.utter_custom_json({"specialization": "all",
                                                  "symptoms": symptoms, "free_text": free_text})
                    break
                elif "bunch of expert psychologists" in msg:
                    dispatcher.utter_custom_json({"specialization": "Psychiatry",
                                                  "symptoms": symptoms, "free_text": free_text})
                    break
                else:
                    dispatcher.utter_custom_json({"specialization": "physical_health_doctors",
                                                  "symptoms": symptoms, "free_text": free_text})
                    break

        return []
