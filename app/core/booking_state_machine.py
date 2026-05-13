from transitions import Machine


class BookingStateMachine:
    states = ["reserved", "confirmed", "cancelled"]

    transitions = [
        {"trigger": "confirm", "source": "reserved", "dest": "confirmed"},
        {"trigger": "cancel", "source": "reserved", "dest": "cancelled"},
        {"trigger": "cancel", "source": "confirmed", "dest": "cancelled"},
    ]

    # Maps the action string the API receives to the trigger method name.
    # The API uses past-tense ("confirmed", "cancelled") but transitions
    # lib methods are present-tense verbs ("confirm", "cancel").
    ACTION_TO_TRIGGER: dict[str, str] = {
        "confirmed": "confirm",
        "cancelled": "cancel",
    }

    def __init__(self, current_state: str) -> None:
        self.machine = Machine(
            model=self,
            states=BookingStateMachine.states,
            transitions=BookingStateMachine.transitions,
            initial=current_state,
            ignore_invalid_triggers=False,
        )

    def apply(self, action: str) -> str:
        trigger_name = self.ACTION_TO_TRIGGER.get(action, action)
        trigger = getattr(self, trigger_name, None)
        if not trigger:
            raise ValueError(f"Invalid action: {action}")
        trigger()
        return self.state  # self.state is what transitions lib updates
