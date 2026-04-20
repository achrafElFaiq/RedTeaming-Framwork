import sqlite3
from pyrit.models.attack_result import AttackResult as PyritAttackResult
from pyrit.models.attack_result import AttackOutcome
from core.results.normalizer import Normalizer
from datetime import datetime
from core.results.attack_result import AttackResult, Conversation, ConversationTurn

class PyritNormalizer(Normalizer):

    def __init__(self, pyrit_result: PyritAttackResult, 
                 db_path: str, target_url: str, attack_name: str):
        self.pyrit_result = pyrit_result
        self.db_path = db_path
        self.target_url = target_url
        self.attack_name = attack_name

    def normalize(self) -> AttackResult:
        print("[PyritNormaliser] Début de la normalisation chronologique.")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        main_id = self.pyrit_result.conversation_id
        active_ids = list(self.pyrit_result.get_active_conversation_ids())
        
        
        print(f"[PyritNormaliser] Conversation IDs actifs : {active_ids}")
        print(f"[PyritNormaliser] Conversation ID principal : {main_id}")
        if not active_ids:
            print("[PyritNormaliser] Aucun active_ids trouvé.")
            return self._build_empty_result()

        placeholders = ",".join("?" * len(active_ids))

        # Étape 1 : On récupère uniquement les requêtes de l'utilisateur (les attaques)
        cursor.execute(f"""
            SELECT id, original_value, timestamp, conversation_id
            FROM PromptMemoryEntries
            WHERE conversation_id IN ({placeholders})
            AND role = 'user'
            ORDER BY timestamp ASC
        """, active_ids)

        user_rows = cursor.fetchall()
        print(f"[PyritNormaliser] {len(user_rows)} requêtes 'user' trouvées.")

        turns = []
        turn_number = 1

        # Étape 2 : Pour chaque requête, on cherche la réponse qui a suivi immédiatement
        for user_row in user_rows:
            prompt_value = user_row['original_value']
            user_timestamp = user_row['timestamp']
            
            # On cherche le premier 'assistant' après ce timestamp
            cursor.execute("""
                SELECT id, original_value, timestamp
                FROM PromptMemoryEntries
                WHERE timestamp > ?
                AND role = 'assistant'
                ORDER BY timestamp ASC
                LIMIT 1
            """, (user_timestamp,))
            
            assistant_row = cursor.fetchone()

            score = False
            rationale = "Aucun score trouvé."
            response_value = "⚠️ Aucune réponse trouvée."

            if assistant_row:
                response_value = assistant_row['original_value']
                print(f"[PyritNormaliser] Turn {turn_number} : Réponse trouvée à {assistant_row['timestamp']}")

                # Étape 3 : On cherche le score lié à l'ID de cette réponse
                cursor.execute("""
                    SELECT score_value, score_rationale
                    FROM ScoreEntries
                    WHERE prompt_request_response_id = ?
                    LIMIT 1
                """, (assistant_row['id'],))

                score_row = cursor.fetchone()
                if score_row:
                    score = score_row['score_value'] == "True"
                    rationale = score_row['score_rationale']

            turns.append(ConversationTurn(
                turn=turn_number,
                prompt=prompt_value,
                response=response_value,
                score=score,
                rationale=rationale
            ))
            turn_number += 1

        conn.close()
        self._clear_db()
        conversation = Conversation(
            conversation_id=self.pyrit_result.conversation_id,
            objective=self.pyrit_result.objective,
            achieved=self.pyrit_result.outcome == AttackOutcome.SUCCESS,
            turns=turns
        )

        return AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=conversation
        )
        
    def _build_empty_result(self) -> AttackResult:
        # Méthode utilitaire pour générer un résultat vide proprement
        result = AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=Conversation(
                conversation_id=self.pyrit_result.conversation_id,
                objective=self.pyrit_result.objective,
                achieved=False,
                turns=[]
            )
        )
        self._clear_db()
        return result
    

    def _clear_db(self):
        print("[PyritNormaliser] Nettoyage de la base de données.")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM PromptMemoryEntries")
            cursor.execute("DELETE FROM ScoreEntries")
            cursor.execute("DELETE FROM AttackResultEntries")
            conn.commit()
            print("[PyritNormaliser] Tables vidées avec succès.")
        except Exception as e:
            print(f"[PyritNormaliser] Erreur lors du nettoyage : {e}")
        finally:
            conn.close()