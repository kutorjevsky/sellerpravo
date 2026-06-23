from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_name = State()
    waiting_role = State()


class NewTask(StatesGroup):
    court = State()
    court_custom = State()
    case_name = State()
    case_number = State()
    client = State()
    description = State()
    notes = State()
    has_poa = State()
    date = State()
    confirm = State()


class TaskResult(StatesGroup):
    entering_result = State()
    entering_fail_reason = State()


class AssistantSchedule(StatesGroup):
    date = State()
    court = State()
