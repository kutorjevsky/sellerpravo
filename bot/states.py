from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    name = State()
    role = State()


class NewTask(StatesGroup):
    client = State()
    organ_type = State()
    organ = State()
    address = State()
    case = State()
    task_type = State()
    action = State()
    success = State()
    deadline = State()
    priority = State()
    poa = State()
    notes = State()
    confirm = State()


class Comment(StatesGroup):
    text = State()


class Result(StatesGroup):
    text = State()
    proof = State()


class FailReason(StatesGroup):
    text = State()


class Assign(StatesGroup):
    plan_date = State()


class SetPlanDate(StatesGroup):
    value = State()


class EditTask(StatesGroup):
    value = State()


class Search(StatesGroup):
    query = State()
