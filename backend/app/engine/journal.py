"""Deterministic state-change journal; replay is the source of tablet data.

The compatibility engine still advances weeks. No new time conversion is guessed.
"""
from copy import deepcopy


class Journal:
    def __init__(self, events=None):
        self.events = deepcopy(events or [])

    @property
    def state(self):
        current = {}
        for event in self.events:
            current = self.apply(current, event)
        return current

    @staticmethod
    def apply(current, event):
        if event["type"] != "state_change":
            return current
        path = event["path"]
        if not path:
            return deepcopy(event["new_state"])
        target = current
        for key in path[:-1]:
            target = target[key]
        if event.get("operation") == "remove":
            target.pop(path[-1], None)
        else:
            target[path[-1]] = deepcopy(event["new_state"])
        return current

    def append(self, *, period, element, old, new, cause, path, operation="set", kind="state_change", message=""):
        self.events.append(dict(sequence=len(self.events) + 1, time={"unit": "week", "period": period},
                                element=element, old_state=deepcopy(old), new_state=deepcopy(new),
                                cause=cause, path=path, operation=operation, type=kind, message=message))

    def capture(self, state, cause="regle"):
        previous = self.state
        period = state["current_week"]
        if not self.events:
            self.append(period=period, element="SYS-MONDE-01", old=None, new=state, cause=cause, path=[])
            return

        def compare(old, new, path, element):
            if old == new:
                return
            if isinstance(old, dict) and isinstance(new, dict):
                for key in sorted(old.keys() | new.keys()):
                    if key not in new:
                        self.append(period=period, element=element, old=old[key], new=None, cause=cause,
                                    path=path + [key], operation="remove")
                    elif key not in old:
                        self.append(period=period, element=element, old=None, new=new[key], cause=cause, path=path + [key])
                    else:
                        compare(old[key], new[key], path + [key], str(new.get("id", new.get("sku", element))))
            elif (isinstance(old, list) and isinstance(new, list) and len(old) == len(new)
                  and all(isinstance(item, dict) for item in old + new)
                  and [item.get("id", item.get("sku")) for item in old] == [item.get("id", item.get("sku")) for item in new]):
                for index, (before, after) in enumerate(zip(old, new)):
                    compare(before, after, path + [index], str(after.get("id", after.get("sku", element))))
            else:
                self.append(period=period, element=element, old=old, new=new, cause=cause, path=path)

        compare(previous, state, [], "SYS-MONDE-01")

    def refusal(self, period, element, value, message):
        self.append(period=period, element=element, old=None, new=value, cause="decision", path=[],
                    kind="refusal", message=message)

    def note(self, period, element, message, *, cause="regle", department="production"):
        self.append(period=period, element=element, old=None, new=None, cause=cause,
                    path=[], kind="event", message=message)
        self.events[-1]["department"] = department

    def history(self):
        state, periods = {}, {}
        for event in self.events:
            state = self.apply(state, event)
            if state.get("started"):
                periods[event["time"]["period"]] = dict(period=event["time"]["period"], **deepcopy(state["kpis"]))
        return list(periods.values())
