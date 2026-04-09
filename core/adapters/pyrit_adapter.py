from pyrit.prompt_target.common.prompt_target import PromptTarget
from pyrit.models.message import Message
from pyrit.models.message_piece import MessagePiece
from core.entities.attack_target import AttackTarget
from core.adapters.adapter import Adapter

class PyritAdapter(Adapter):

    def wrap(self, target: AttackTarget) -> PromptTarget:

        class OrangePromptTarget(PromptTarget):

            async def send_prompt_async(self, *, message: Message) -> list[Message]:
                # extract prompt text from incoming message
                prompt = message.message_pieces[0].converted_value

                # call your SIA
                response = target.query(prompt) or ""

                # wrap response back into PyRIT format
                response_piece = MessagePiece(
                    role="assistant",
                    original_value=response,
                    converted_value=response,
                )
                return [Message(message_pieces=[response_piece])]

        return OrangePromptTarget(endpoint=target.url)