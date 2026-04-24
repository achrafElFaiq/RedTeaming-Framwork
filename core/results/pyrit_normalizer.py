import sqlite3

from pyrit.memory.central_memory import CentralMemory
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
        print("[PyritNormaliser] Début de la normalisation.")
        memory = CentralMemory.get_memory_instance()

        active_ids = list(self.pyrit_result.get_active_conversation_ids())
        if not active_ids:
            print("[PyritNormaliser] Aucun id trouvé.")
            return self._build_empty_result()

        turns = []
        turn_number = 1

        for conv_id in active_ids:
            pieces = memory.get_message_pieces(conversation_id=conv_id)
            pieces_sorted = sorted(pieces, key=lambda p: p.sequence)

            i = 0
            while i < len(pieces_sorted) - 1:
                user_piece = pieces_sorted[i]
                assistant_piece = pieces_sorted[i + 1]

                if user_piece.role == "user" and assistant_piece.role == "assistant":
                    score = False
                    rationale = "Aucun score trouvé."

                    scores = memory.get_prompt_scores(prompt_ids=[assistant_piece.id])
                    if scores:
                        score = scores[0].get_value() == True
                        rationale = scores[0].score_rationale

                    turns.append(ConversationTurn(
                        turn=turn_number,
                        prompt=user_piece.original_value,
                        response=assistant_piece.original_value,
                        score=score,
                        rationale=rationale
                    ))
                    turn_number += 1
                    i += 2
                else:
                    i += 1

        #self._clear_db()

        conversation = Conversation(
            conversation_id=self.pyrit_result.conversation_id,
            objective=self.pyrit_result.objective,
            achieved=self.pyrit_result.outcome == AttackOutcome.SUCCESS,
            turns=turns
        )

        print("[PyritNormaliser] Fin de la normalisation.")

        return AttackResult(
            framework="pyrit",
            attack_name=self.attack_name,
            target_url=self.target_url,
            timestamp=datetime.now(),
            conversation=conversation
        )

    def _build_empty_result(self) -> AttackResult:
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
        #self._clear_db()
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