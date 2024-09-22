from typedb.client import *
import os


class Database:
    def __init__(self, db_name):
        self.client = TypeDB.core_client("18.143.49.142:1729""")
        self.session = self.client.session(db_name, SessionType.DATA)

    def get_correlated_symptoms(self, symptom):
        qry = f"""
                 match $s1 isa symptoms, has symptom_name "{symptom}"; $s2 isa symptoms, has symptom_name $sn; 
                 $ss(symptom1:$s1, symptom2:$s2) isa symptom_symptom, 
                 has weight $w; get $sn, $w; 
                """
        with self.session.transaction(TransactionType.READ) as read_tx:
            answer = read_tx.query().match(qry)
            symptom_weight = {}
            for ans in answer:
                symptom_weight.update(
                    {ans.get("sn").get_value(): ans.get("w").get_value()})
            sorted_symptom_weight = dict(
                sorted(symptom_weight.items(), key=lambda item: item[1], reverse=True))
            read_tx.close()
        print(sorted_symptom_weight)
        return sorted_symptom_weight

    def get_all_symptoms_name(self):
        """

        Returns all english symptom name from database.

        Returns
        -----------
        symptom_list: list
        """
        qry = "match $s isa symptoms, has symptom_name $sn; get $sn;"
        with self.session.transaction(TransactionType.READ) as read_tx:
            answer = read_tx.query().match(qry)
            listt = []
            for ans in answer:
                a = ans.get("sn").get_value()
                listt.append(a)
            read_tx.close()
        return listt

    def eng_syn_to_sym(self, symptom):
        """

        Translates english synonym into english symptom.

        Parameters
        --------------
        symptom: str

        Returns
        -----------
        sym: str
        """

        with self.session.transaction(TransactionType.READ) as read_transaction:
            qry = f"""
                    match $s isa symptoms, has symptom_name $sn, has english_synonyms $es; $es =
                    "{symptom}"; get $sn;
                """
            answer = read_transaction.query().match(qry)
            sym = ""
            for ans in answer:
                sym = ans.get("sn").get_value()
            if sym == "":
                qry = f"""
                        match $s isa symptoms, has symptom_name $sn, has english_synonyms $es; 
                        {{$es contains "{symptom}|";}} 
                        or {{$es contains "|{symptom}|";}} or {{$es contains "|{symptom}";}} ; 
                        get $sn; 
                       """

                answer = read_transaction.query().match(qry)
                for ans in answer:
                    sym = ans.get("sn").get_value()
                if sym == "":
                    return symptom
            return sym

    def get_parent_symptom(self, symptom):
        """

        Returns parent symptom of a given symptom.

        Parameters
        --------------
        symptom: str

        Returns
        -----------
        parent: str
        """
        qry = f"""
                     match $s isa symptoms, has symptom_name "{symptom}", has parent_symptom_name $ps; get $ps;
              """
        with self.session.transaction(TransactionType.READ) as read_tx:
            answer = read_tx.query().match(qry)
            parent = ""
            for ans in answer:
                parent = ans.get("ps").get_value()
            read_tx.close()
        return parent
