import sys
import sqlite3
import readline
from random import randrange
from base64 import b64encode

GREEN = '\033[32m'
RED = '\033[91m'
BLUE = '\033[34m'
YELLOW = '\033[33m'
PURPLE = '\033[95m'
RESET = '\033[0m'

DIRECTIONS = ['east', 'west', 'north', 'south', 'up', 'down']
SUPER_COMMANDS = ['loot','spawn','vanish','dig','place','tele','map','table']
NORMAL_COMMANDS = ['use', 'look', 'go', 'super', 'normal', 'inspect', 'equip', 'drop', 'attack', 'list', 'stats', 'items']
help = {'loot':'<name> <min> <max> | <desc>','spawn':'<name> <hp> <item>','vanish':'', 'dig':'<dir> <rev> | <name> | <description>','place':'<item>','tele':'<room_id>','map':'','table':'<table name>', 'look':'','go':'<dir> | <dir>','super':'<passcode>','normal':'','inspect':'<item>','equip':'<item>','drop':'<item>','attack':'<mob> | <player> ','list':'','stats':'','items':'','use':'<item>'}

type = lambda x: "damage" if x>0 else "hp"
error = lambda msg: print(YELLOW + msg + RESET)
event = lambda msg: print(BLUE + msg + RESET)

color_health = lambda x: GREEN if x > 50 else YELLOW if x > 25 else RED
color_attack = lambda x: GREEN if x < 50 else YELLOW if x < 25 else RED

class Dungeon:
    """
    Note:
    - Commands with "continue" don't progress clock/attack schedule
    - super user has elevated permissions to modify the world but can't
      interact/fight mobs
    """
    visited = []   # tracks rooms visited this session
    filename = "dungeon.map"
    online = []

    def updates(self):
        self.c.execute('SELECT username FROM user WHERE status="online"')
        x = self.c.fetchall()
        new_usr = [i[0] for i in x if i not in self.online and i[0] != self.user]
        if new_usr != self.online and len(new_usr) > 0:
            if new_usr != []:
                users = ", ".join(new_usr)
                print(GREEN + "{} online".format(users) + RESET)
                self.online = new_usr
        if len(new_usr) < len(self.online):
            old_usr = [i for i in self.online if i not in x and i != self.user]
            users = ", ".join(old_usr)
            error("{} offline".format(users))
            self.online = new_usr

    def update_usr(self):
        self.c.execute('UPDATE user SET health={}, attack={}, room_id={}, super={} WHERE username="{}"'.format(self.health, self.attack, self.current_room, int(self.super), self.user))
        self.db.commit()

    def combat(self):
        self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
        mobs = self.c.fetchall() # todo: have multiple mobs at once
        if mobs is not None:
            for mob in mobs:
                self.c.execute('SELECT damage FROM item WHERE owner="{}"'.format(mob[1]))
                damage = self.c.fetchone()
                if damage is not None:
                    print(mob[1] + " attacked you! You lost " + str(damage[0])+ " health")
                    self.health -= damage[0]
                    self.update_usr()
                else:
                    error("Error reading item")

    def is_dead(self):
        if self.health <= 0:
            error("you died...")
            print("you seemed to have lost your items and ended up back at the entrance")
            self.health = 100
            self.attack = 5
            for item in self.items:
                self.place(item,self.user) # drops current items into old room
            self.current_room = 1
            self.items = []
            self.update_usr()

    def repl(self):
        self.doLook()
        while True:
            self.updates()
            line = input(self.prompt)
            words = line.split()

            if len(words) == 0:
                continue
            elif words[0] in ('exit', 'quit', 'q'):
                self.update_usr()
                print("Saved")
                self.db.close()
                break

            elif words[0] in SUPER_COMMANDS:
                if self.super:
                    self.super_com(words)
                else:
                    print("must be super user to do that try: \'super\'")
                continue

            elif words[0] == 'look':
                self.doLook()

            elif words[0] == 'go' or words[0] in DIRECTIONS:
                # move to an adjacent room.
                if len(words) < 2 and words[0] not in DIRECTIONS:
                    print("usage: go {}".format(help[words[0]]))
                    continue
                dir = words[0] if words[0] in DIRECTIONS else words[1]
                self.c.execute("SELECT to_room FROM exits WHERE from_room = {} AND dir='{}'".format(self.current_room, dir))
                new_room_p = self.c.fetchone()
                if new_room_p is None:
                    error("You can't go that way")
                    continue
                else:
                    self.current_room = new_room_p[0]
                    self.visited.append(self.current_room)
                    self.doLook()
                    self.update_usr()

            elif words[0] == 'super':
                if len(words) != 1 and words[1] == '*':  # add a password here (must be one string with no spaces)
                    self.prompt = RED + self.user + " ! " + RESET
                    self.super = True
                    self.update_usr()
                    continue
                else:
                    print("usage: super <passcode>")

            elif words[0] == 'normal':
                self.prompt = self.user + " > "
                self.super = False
                self.update_usr()
                continue

            elif words[0] == 'inspect':
                if self.super:  # inspect any item
                    self.c.execute("SELECT name FROM loot".format(self.current_room))
                    for item in self.c.fetchall():
                        print("{}  ".format(item[0]), end='')
                    print("")
                    name = input("Pick an item to inspect: ")
                    self.c.execute("SELECT * FROM loot WHERE name='{}'".format(name))
                    item = self.c.fetchone()
                    if item is not None:
                        print(item[1] + ": " + item[4] + ", {}: [{}-{}]".format(type(item[2]), abs(item[2]),abs(item[3])))
                else: # inspect any item in the room
                    if len(words) > 1:
                        self.c.execute("SELECT * FROM item WHERE room_id='{}'".format(self.current_room))
                        items = self.c.fetchall()
                        if items is not None:
                            for item in items:
                                if item[1] == words[1]:
                                    print("{} {}, {} | {}".format(item[1], abs(item[2]), type(item[2]), item[3]))
                continue

            elif words[0] == 'drop':
                if len(words) < 2:
                    print("usage: drop {}".format(help[words[0]]))
                    continue
                if words[1] in self.items:
                    self.c.execute('UPDATE item SET owner="",room_id={} WHERE owner="{}" AND name="{}"'.format(self.current_room, self.user, words[1]))
                    self.db.commit()
                    self.update_usr()
                    while words[1] in self.items:
                        self.items.remove(words[1])
                        print("You dropped your {}".format(words[1]))
                    continue
                else:
                    error("Not a valid item")

            elif words[0] == 'attack':
                if len(words) < 2:
                    print("usage: attack {}".format(help[words[0]]))
                    continue
                self.c.execute('SELECT * FROM mobs WHERE room_id={} AND desc="{}"'.format(self.current_room, words[1]))
                mob = self.c.fetchone() # if two mobs have the same name attack just one
                if mob is None:
                    error("Not a valid mob")
                else:
                    if randrange(200) < 180: # todo: more player/mob stats
                        if mob[2] <= self.attack:
                            self.c.execute("DELETE FROM mobs WHERE room_id={}".format(self.current_room))
                            print("You killed {}!".format(mob[1]))
                            self.c.execute('SELECT name FROM item WHERE owner="{}"'.format(mob[1]))
                            item = self.c.fetchone()
                            print("It dropped a {}".format(item[0]))
                            self.place(item[0])
                        else:
                            damage = mob[2] - self.attack
                            self.c.execute("UPDATE mobs SET health={} WHERE room_id={} AND desc='{}'".format(damage,self.current_room,words[1]))
                            self.db.commit()
                            print("You did {} damage to {}. {} has {} health left".format(self.attack, mob[1], mob[1],mob[2]-self.attack))
                    else:
                        print("{} dodged your attack!!".format(mob[1]))

            elif words[0] == 'list':
                self.c.execute('SELECT * FROM user')
                super = lambda y,x: RED + x+ RESET if bool(y) else x
                online = lambda y: GREEN + y + RESET if 'online' in y else y
                print("name     | hp    | dmg | room | status  |" if self.super else "name     | status  |")
                for i in self.c.fetchall():
                    if self.super:
                        print(super(i[5],'{0: <8}'.format(i[0])) + " | " + color_health(i[2])+ '{0: <5}'.format(i[2]) + RESET + " | " + color_attack(i[3]) + '{0:<3}'.format(i[3]) + RESET + " | " + '{0: <4}'.format(i[4]) + " | " + online('{0: <7}'.format(i[6])) + " |") # fix formatting here for names
                    else:
                        print(super(i[5],'{0: <8}'.format(i[0]))+ " | " + online('{0: <7}'.format(i[6])) + " |") # fix formatting here for names

            elif words[0] == 'stats':
                print("You have " + color_health(self.health) + str(self.health) + RESET + " health")
                print("Your attack is " + color_attack(self.attack) + str(self.attack) + RESET)
                print("You have {} items".format(len(self.items)))
                continue

            elif words[0] == 'items':
                for item in set(self.items):
                    self.c.execute('SELECT * from item WHERE name="{}" and owner="{}"'.format(item,self.user))
                    x = self.c.fetchall()
                    if x is not None:
                        for p in x:
                            print("{}, {} | {} {}".format(p[1],p[3],abs(p[2]),type(p[2])))
                continue


            elif words[0] == 'equip' or words[0] == 'use':
                if len(words) < 2:
                    print("usage: {} {}".format(words[0], help[words[0]]))
                    continue
                self.c.execute('SELECT * from item WHERE name="{}" and owner="{}"'.format(words[1],self.user))
                x = self.c.fetchall()
                if len(x) == 0:
                    error("not a valid item")
                    continue
                elif len(x) > 1:
                    for j,i in enumerate(x):
                        print("{} | {} | {} {}".format(j,i[1] ,abs(i[2]),"damage" if words[0]=='equip' else 'hp'))
                    try:
                        index = int(input("pick one: "))
                    except:
                        error("not a valid index")
                        continue
                else:
                    index = 0
                if x[index][2] > 0 and words[0] == 'equip':
                    self.attack = x[index][2]
                    print("Your attack is " + color_attack(self.attack) + str(self.attack) + RESET)
                    self.update_usr()
                elif x[index][2] < 0 and words[0] == 'use':
                    self.health += abs(x[index][2])
                    print("You healed {} hp (total: {})".format(abs(x[index][2]), self.health))
                    self.update_usr()
                    self.items.remove(words[1])
                    self.c.execute('DELETE FROM item WHERE owner="{}" AND name="{}" AND damage={}'.format(self.user, words[1],x[index][2]))
                    self.db.commit()
                else:
                    error("Can't {} that: try '{}'".format(words[0], words[0] and 'equip'))
                    continue


            elif words[0] == 'take':
                self.c.execute('SELECT * FROM item WHERE room_id={}'.format(self.current_room))
                item = self.c.fetchall()
                if len(words) < 2:
                    print("usage: take {}".format(help[words[0]]))
                    continue
                if item != []:
                    for x in item:
                        if words[1] == x[1]:
                            self.items.append(x[1])
                            self.c.execute('UPDATE item SET owner="{}" WHERE room_id={} AND name="{}"'.format(self.user,self.current_room,x[1]))
                            self.c.execute('UPDATE item SET room_id=-1 WHERE owner="{}" AND name="{}"'.format(self.user,x[1]))
                            self.db.commit()
                            break

            elif words[0] == 'help':
                if self.super:
                    print(RED, end='')
                    for i in SUPER_COMMANDS:
                        print("{0: <8}".format(i) + " | "+ '{}'.format(help[i]))
                    print(RESET,end='')
                for j in NORMAL_COMMANDS:
                    print("{0: <8}".format(j) + " | "+ '{}'.format(help[j]))
                continue

            else:
                print("unknown command {}".format(words[0]))
                continue

            if not self.super:
                self.combat()
                self.is_dead()

    # helper function to place an item in current room
    def place(self, name, owner=""):
        if owner == "":
            self.c.execute("SELECT * FROM loot WHERE name='{}'".format(name))
            item = self.c.fetchone()
            damage = randrange(item[2],item[3]) # takes damage from range instead of int
            self.c.execute('INSERT INTO item (name, damage, desc, room_id) VALUES ("{}",{},"{}",{})'.format(name,damage,item[4], self.current_room))
        else:
            self.c.execute("UPDATE item SET room_id='{}', owner='{}' WHERE owner='{}'".format(self.current_room,"",owner))
        self.db.commit()

    # describe this room and its exits
    def doLook(self):
        self.c.execute("SELECT short_desc FROM rooms WHERE id={}".format(self.current_room))
        print(self.c.fetchone()[0])
        self.c.execute("SELECT florid_desc FROM rooms WHERE id={}".format(self.current_room))
        print(self.c.fetchone()[0])
        self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
        mobs = self.c.fetchall()
        if mobs != None and mobs != []:
            for mob in mobs:
                self.c.execute('SELECT name FROM item WHERE owner="{}"'.format(mob[1]))
                x = self.c.fetchone()
                print("There is an " + mob[1] + " with " + str(mob[2]) + " health, carrying a " + x[0])
        self.c.execute("SELECT name FROM item WHERE room_id={}".format(self.current_room))
        items = self.c.fetchall()
        if items != []:
            print("This room contains: ", end='')
            for item in items:
                print("{}  ".format(item[0]), end='')
            print("")
        self.c.execute("SELECT dir FROM exits WHERE from_room={}".format(self.current_room))
        print("There are exits in these directions: ", end='')
        for exit in self.c.fetchall():
            print("{}  ".format(exit[0]), end='')
        print("")

    def login(self):
        self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
        db_exists = self.c.fetchone()
        if (db_exists is None):
            self.c.execute("DROP TABLE if exists rooms")
            self.c.execute("DROP TABLE if exists mobs")
            self.c.execute("DROP TABLE if exists loot")
            self.c.execute("DROP TABLE if exists exits")
            self.CreateDatabase()
            self.user = input("username: ")
            self.newuser()
            return None
        self.user = input("username: ")
        self.c.execute('SELECT * FROM user WHERE username="{}"'.format(self.user)) # if a username exists
        if self.c.fetchall() == []:
            self.newuser()
        else:
            self.authenticate()

    def newuser(self):
        psw = input("create a password for '{}': ".format(self.user))
        self.prompt = self.user + ' > '
        self.super = False # base user is normal not super
        self.attack = 5  # base attack "punch"
        self.health = 100  # base player health
        self.items = []  # base player inventory is empty
        self.c.execute("SELECT MIN(id) FROM rooms")
        self.current_room = self.c.fetchone()[0]
        self.c.execute('INSERT INTO user (username, password, health, attack, room_id, super, status) VALUES ("{}","{}",{},{},{},{},"{}")'.format(self.user,b64encode(psw.encode("utf-8")),self.health,self.attack,1,int(self.super),"online"))
        self.db.commit()

    def authenticate(self):
        psw = input("password: ")
        self.c.execute('SELECT * FROM user WHERE username="{}" AND password="{}"'.format(self.user,b64encode(psw.encode("utf-8"))))
        correct = self.c.fetchone()
        if correct is None or len(correct) < 4:
            print("Incorrect password for user")
            self.login()
            return None
        if correct[5] == 1:
            self.prompt =  RED + self.user + " ! "+RESET
            self.super = True
        else:
            self.prompt = self.user + ' > '
            self.super = False
        self.current_room = correct[4]
        self.health = correct[2]  # base player health
        self.items = []  # base player inventory
        self.attack = correct[3] # base attack
        self.c.execute('SELECT name FROM item WHERE owner = "{}"'.format(self.user))
        for item in self.c.fetchall():
            self.items.append(item[0])
        self.c.execute('UPDATE user SET status="online" WHERE username="{}"'.format(self.user))
        self.db.commit()

    # handle startup
    def CreateDatabase(self):
        self.c.execute("CREATE TABLE rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, short_desc TEXT, florid_desc TEXT)")
        self.c.execute("CREATE TABLE mobs (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, health INTEGER, loot TEXT, room_id INTEGER)")
        self.c.execute("CREATE TABLE loot (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min INTEGER, max INTEGER, desc TEXT)") # items have range of damage
        self.c.execute("CREATE TABLE item (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, damage INTEGER, desc TEXT, room_id INTEGER, owner TEXT)") # specific items have damage value
        self.c.execute("CREATE TABLE exits (from_room INTEGER, to_room INTEGER, dir TEXT)")
        self.c.execute("CREATE TABLE user (username TEXT, password TEXT, health INTEGER, attack INTEGER, room_id INTEGER, super INTEGER, status TEXT)")
        self.c.execute("INSERT INTO rooms (florid_desc, short_desc) VALUES ('You are standing at the entrance of what appears to be a vast, complex cave.', 'entrance')")
        self.db.commit()

    def spawn(self, name, health, loot):
        damage = randrange(loot[2],loot[3]) # finds damage value in range
        query = 'INSERT INTO mobs (desc, health, loot, room_id) VALUES ("{}", {}, "{}", {})'.format(name, int(damage), health, self.current_room)
        self.c.execute(query)
        event("{} spawned with {}hp and a {} in room# {}".format(name, health, loot[1], self.current_room))
        self.c.execute('INSERT INTO item (name, damage, desc, room_id, owner) VALUES ("{}",{},"{}",{},"{}")'.format(loot[1],damage, loot[4], -1, name))
        self.db.commit()

    def super_com(self, words):
        if words[0] == 'dig':
            # Only super users can create new rooms
            line = " ".join(words)
            descs = line.split("|")
            words = descs[0].split()
            if len(words) < 3 or len(descs) != 3:
                print("usage: dig {}".format(help[words[0]]))
                return
            forward = words[1]
            reverse = words[2]
            if forward not in DIRECTIONS or reverse not in DIRECTIONS:
                print(RED + "Not a valid direction, try " + RESET + str(DIRECTIONS))
                return
            brief = descs[1].strip()   # strip removes whitespace around |'s
            florid = descs[2].strip()
            # now that we have the directions and descriptions,
            # add the new room, and stitch it in to the dungeon
            # via its exits
            query = 'INSERT INTO rooms (short_desc, florid_desc) VALUES ("{}", "{}")'.format(brief, florid)
            self.c.execute(query)
            new_room_id = self.c.lastrowid
            # now add tunnels in both directions
            query = 'INSERT INTO exits (from_room, to_room, dir) VALUES ({}, {}, "{}")'.format(self.current_room, new_room_id, forward)
            self.c.execute(query)
            query = 'INSERT INTO exits (from_room, to_room, dir) VALUES ({}, {}, "{}")'.format(new_room_id, self.current_room, reverse)
            self.c.execute(query)
            self.db.commit()

        elif words[0] == 'place':
            if len(words) < 2:
                print("usage: place {}".format(help[words[0]]))
                return
            self.place(words[1])
            event("{} placed in room #{}".format(words[1],self.current_room))

        elif words[0] == 'tele':
            if len(words) < 2:
                print("usage: tele {}".format(help[words[0]]))
                return
            self.c.execute('SELECT id FROM rooms')
            x = [row[0] for row in self.c.fetchall()]
            if int(words[1]) in x:
                self.current_room = int(words[1])
                event("You teleported!")
                self.doLook()
                self.update_usr()
            else:
                print("Not a valid id")
                return

        elif words[0] == 'map':
            self.c.execute('SELECT * FROM rooms')
            x = self.c.fetchall()
            print("id| Description | Long Description |")
            for i in x:
                print("{} | {} | {}|".format(i[0], i[1], i[2]))

        elif words[0] == 'vanish':
            query = "DELETE FROM mobs WHERE room_id={}".format(self.current_room) # deletes all mobs in current room
            self.c.execute(query)
            self.doLook()

        elif words[0] == 'spawn':
            if len(words) < 4 or not words[2][-1:].isdigit():
                print("usage: spawn {}".format(help[words[0]]))
                return
            self.c.execute('SELECT * FROM loot WHERE name = "{}"'.format(words[3]))
            loot = self.c.fetchall()
            if (loot is None or loot == []):
                error("that isn't valid loot, try adding it with \'loot {}...\'".format(words[3]))
                return
            self.spawn(words[1], words[2], loot[0])

        elif words[0] == 'loot':
            if len(words) < 4 or not words[2][-1:].isdigit() or not words[3][-1:].isdigit():
                print("usage: loot {}".format(help[words[0]]))
                return
            line = " ".join(words)
            descs = line.split("|")
            words = descs[0].split()
            query = 'INSERT INTO loot (name, min, max, desc) VALUES ("{}", {}, {}, "{}")'.format(words[1].strip(), int(words[2]), int(words[3]), descs[1].strip())
            self.c.execute(query)
            self.db.commit()

        elif words[0] == "table":
            if len(words) < 2:
                print("usage: table {}".format(help[words[0]]))
                return
            try:
                self.c.execute("SELECT * FROM {}".format(words[1]))
                x = self.c.fetchall()
            except:
                error("not a valid table")
                return
            for i in x:
                for j in i:
                    print("{} | ".format(j),end='')
                print("")

assert sys.version_info >= (3,0), "This program requires Python 3"

histfile = ".shell-history"

if __name__ == '__main__':
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        open(histfile, 'wb').close()

    d = Dungeon()
    d.db = sqlite3.connect(d.filename)
    d.c = d.db.cursor()
    d.login()
    print("Welcome to the dungeon. Try 'look' 'go' and 'dig'")
    d.repl()
