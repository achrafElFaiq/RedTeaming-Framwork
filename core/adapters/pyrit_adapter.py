from pyrit.prompt_target.common.prompt_target import PromptTarget
from pyrit.models.message import Message
from pyrit.models.message_piece import MessagePiece
from core.entities.attack_target import AttackTarget
from core.adapters.adapter import Adapter

from pyrit.prompt_target.common.target_capabilities import TargetCapabilities


class PyritAdapter(Adapter):

    def wrap(self, target: AttackTarget) -> PromptTarget:

        class OrangePromptTarget(PromptTarget):
            
            def __init__(self, *args, **kwargs):
                # On définit les capacités comme tu l'as vu dans la doc
                caps = TargetCapabilities(
                    supports_multi_turn=True,
                    supports_multi_message_pieces=True
                )
                
                # On passe caps au parent via l'argument officiel 'custom_capabilities'
                super().__init__(*args, custom_capabilities=caps, **kwargs)
                
                # On force aussi la variable interne pour la logique d'exécution
                self._supports_multi_turn = True

            @property
            def supports_multi_turn(self) -> bool:
                return True

            async def send_prompt_async(self, *, message: Message) -> list[Message]:
                # Extract the incoming user piece
                user_piece = message.message_pieces[0]
                prompt = user_piece.converted_value

                # Call the SIA
                response = target.query(prompt) or ""

                # Wrap response — MUST inherit conversation_id and sequence from the user piece
                response_piece = MessagePiece(
                    role="assistant",
                    original_value=response,
                    converted_value=response,
                    conversation_id=user_piece.conversation_id,  # ← lien principal
                    sequence=user_piece.sequence + 1,  # ← PyRIT utilise sequence pour get_request_from_response
                )
                return [Message(message_pieces=[response_piece])]

        return OrangePromptTarget(endpoint=target.url)