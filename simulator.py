"""Administrator-controlled test traffic generator for security validation."""
import random, time
from PySide6.QtCore import QThread, Signal
import database as db
import monitor

BAD_COUNTRIES = ["RU", "CN", "NG", "BR", "KP", "VN"]


def _ip():
    return ".".join(str(random.randint(11, 220)) for _ in range(4))


class Simulator(QThread):
    event = Signal(str)

    def __init__(self, mode=None, actor_username=None):
        super().__init__()
        self.mode = mode
        self.actor_username = actor_username
        self._running = True

    def stop(self):
        self._running = False

    def _sleep(self, s):
        end = time.time() + s
        while self._running and time.time() < end:
            time.sleep(0.05)

    def run(self):
        while self._running:
            customers = db.query("SELECT * FROM users WHERE role='customer' AND disabled=0")
            staff = db.query("SELECT * FROM users WHERE role='staff' AND disabled=0")
            if self.mode:
                if self.mode == "brute" and customers: self._brute_force(random.choice(customers))
                elif self.mode == "foreign" and customers: self._foreign(random.choice(customers))
                elif self.mode == "bulk":
                    if self.actor_username:
                        actor = db.get_user(self.actor_username)
                        if actor and not actor.get("disabled", 0):
                            self._bulk_download(actor)
                        else:
                            self.event.emit("Bulk-download validation cancelled: initiating account is unavailable")
                    elif staff:
                        self._bulk_download(random.choice(staff))
                    else:
                        self.event.emit("No eligible staff account available for bulk-download validation")
                else: self.event.emit("No eligible account available for this validation")
                return
            if not customers:
                self._sleep(2); continue
            r = random.random()
            if r < 0.60 or (r >= 0.80 and not staff):
                self._normal_login(random.choice(customers))
            elif r < 0.70:
                self._brute_force(random.choice(customers))
            elif r < 0.78:
                self._foreign(random.choice(customers))
            elif r < 0.90:
                self._normal_file(random.choice(staff))
            else:
                self._bulk_download(random.choice(staff))
            self._sleep(random.uniform(1.5, 4))

    def _normal_login(self, u):
        ok = random.random() < 0.95
        res = monitor.process_login(u["username"], ok, u["home_device"], f"10.0.{random.randint(0, 9)}."
                                    f"{random.randint(2, 250)}", "IN", random.randint(8, 20),
                                    send_notifications=False)
        self.event.emit(f"Normal login {u['username']} -> risk {res['risk']}")

    def _foreign(self, u):
        res = monitor.process_login(u["username"], True, f"unknown-{random.randint(100, 999)}", _ip(),
                                    random.choice(BAD_COUNTRIES), random.choice([1, 2, 3, 4]),
                                    send_notifications=False)
        self.event.emit(f"Odd-hour foreign login {u['username']} -> risk {res['risk']}")

    def _normal_file(self, u):
        res = monitor.process_file(u["username"], f"report_{random.randint(1, 99)}.pdf",
                                   random.choice(["View", "Edit", "Download"]), random.uniform(0.1, 5),
                                   random.randint(0, 2), random.randint(9, 18), send_notifications=False)
        self.event.emit(f"Normal file access {u['username']} -> risk {res['risk']}")

    def _brute_force(self, u):
        dev, ip, ctry, res = f"attacker-{random.randint(100, 999)}", _ip(), random.choice(BAD_COUNTRIES), None
        for _ in range(6):
            if not self._running: return
            res = monitor.process_login(u["username"], False, dev, ip, ctry, random.choice([2, 3, 14]),
                                        send_notifications=False)
            self._sleep(0.3)
        if random.random() < 0.3:
            res = monitor.process_login(u["username"], True, dev, ip, ctry, 3, send_notifications=False)
        self.event.emit(f"BRUTE FORCE on {u['username']} from {ctry} -> risk {res['risk']}")

    def _bulk_download(self, u):
        res = None
        for i in range(25):
            if not self._running: return
            res = monitor.process_file(u["username"], f"customer_db_export_{i}.csv", "Download",
                                       random.uniform(30, 90), 3, random.choice([0, 1, 22, 23]),
                                       send_notifications=False)
            self._sleep(0.1)
        self.event.emit(f"BULK DOWNLOAD by {u['username']} -> risk {res['risk']}")
