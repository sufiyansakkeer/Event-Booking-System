# BookingStateMachine wraps a single booking's state transitions.
# In Dart terms: think of this like a BLoC that only manages state transitions
# and rejects invalid ones — no business logic, just valid state flow.
from transitions import Machine


class BookingStateMachine:
    # All possible states a booking can be in.
    # This is like an enum in Dart — a fixed list of valid values.
    status = ["reserved", "confirmed", "cancelled"]

    # All valid transactions
    # trigger: the method name you call to attempt the transition.
    # source: the state the booking must currently be in.
    # dest:   the state it moves to if the trigger is called.
    transitions = [
        {"trigger": "confirm", "source": "reserved", "dest": "confirmed"},
        {"trigger": "cancel", "source": "reserved", "dest": "cancelled"},
        {"trigger": "cancel", "source": "confirmed", "dest": "cancelled"},
        # cancelled is terminal — no transitions out of it.
    ]

    def __init__(self, current_state: str) -> None:
        # Set the initial state to whatever the booking currently has in DB.
        # This lets us rehydrate the machine from a persisted state,
        # exactly like restoring a BLoC from SharedPreferences.
        self.current_state = current_state

        # Machine wires up all triggers as methods on `self`.
        # After this line, self.confirm() and self.cancel() exist automatically.
        # model=self means the machine controls THIS object's `state` attribute.
        self.machine = Machine(
            model=self,  # attach all state machine to this object , so the machine dynamically adds methods to self.
            states=BookingStateMachine.status,
            transitions=BookingStateMachine.transitions,
            initial=current_state,
            # If you call an invalid transition (e.g. cancel on a cancelled booking),
            # raise an exception instead of silently doing nothing. it will be MachineError
            ignore_invalid_triggers=False,
        )

    def apply(self, action: str) -> str:
        """
        Apply a trigger by name and return the new state.
        Raises MachineError if the transition is invalid.
        """
        # Get the trigger method by name from self (e.g. self.confirm or self.cancel)
        # and call it. `transitions` lib wires these up in __init__ via Machine.
        trigger = getattr(self, action, None)
        if not trigger:
            raise ValueError(f"Invalid action: {action}")
        trigger()  # This will change self.current_state if valid, or raise if invalid. # machine already added in the self this methods
        return self.current_state
