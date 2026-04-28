import logging

from pyrit.prompt_target.common.prompt_target import PromptTarget
from pyrit.models.message import Message
from pyrit.models.message_piece import MessagePiece
from core.models.attack_target import AttackTarget
from core.contracts.adapter import Adapter

from pyrit.prompt_target.common.target_capabilities import TargetCapabilities


logger = logging.getLogger(__name__)


class PyritAdapter(Adapter):

    def wrap(self, target: AttackTarget) -> PromptTarget:

        class OrangePromptTarget(PromptTarget):

            def __init__(self, *args, **kwargs):
                caps = TargetCapabilities(
                    supports_multi_turn=True,
                    supports_multi_message_pieces=True
                )
                super().__init__(*args, custom_capabilities=caps, **kwargs)
                self._supports_multi_turn = True
                self._turn_counter = 0

            @property
            def supports_multi_turn(self) -> bool:
                return True

            async def send_prompt_async(self, *, message: Message) -> list[Message]:
                user_piece = message.message_pieces[0]
                prompt = user_piece.converted_value

                self._turn_counter += 1
                prompt_preview = prompt[:120].replace("\n", " ")
                logger.info(
                    "[Turn %d] (Attacker) → %s",
                    self._turn_counter, prompt_preview,
                )

                response = target.query(prompt) or ""

                response_preview = response[:120].replace("\n", " ")
                logger.info(
                    "[Turn %d] (Target)  → %s",
                    self._turn_counter, response_preview,
                )

                response_piece = MessagePiece(
                    role="assistant",
                    original_value=response,
                    converted_value=response,
                    conversation_id=user_piece.conversation_id,
                    sequence=user_piece.sequence + 1,
                )
                return [Message(message_pieces=[response_piece])]

        return OrangePromptTarget(endpoint=target.url)
