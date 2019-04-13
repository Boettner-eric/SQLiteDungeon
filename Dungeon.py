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
SUPER_COMMANDS = ['loot','spawn','vanish','dig','place','tele','map','table','debug']

def color(num):
    if num > 50:
        return GREEN
    if num > 25:
        return YELLOW
    return RED


class Dungeon:
    """
    Note:
    - Commands with "continue" don't progress clock/attack schedule
    - super user has elevated permissions to modify the world but can't
      interact/fight mobs
    """
    visited = []   # tracks rooms visited this session

    def repl(self):
        self.doLook()
        while True:
            if self.health <= 0:
                print(RED+"you died..."+RESET)
                print("you seemed to have lost your items and ended up back at the entrance")
                self.current_room = 1
                self.health = 100
                self.items = []

            line = input(self.prompt)
            words = line.split()

            if len(words) == 0:
                continue
            elif words[0] in ('exit', 'quit', 'q'):
                self.saveuser()
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
                    print("usage: go <direction> | <direction>")
                    continue
                dir = words[0] if words[0] in DIRECTIONS else words[1]
                self.c.execute("SELECT to_room FROM exits WHERE from_room = {} AND dir='{}'".format(self.current_room, dir))
                new_room_p = self.c.fetchone()
                if new_room_p is None:
                    print("You can't go that way")
                    continue
                else:
                    self.current_room = new_room_p[0]
                    self.visited.append(self.current_room)
                    self.doLook()


            elif words[0] == 'super':
                if len(words) != 1 and words[1] == '*':  # add a password here (must be one string with no spaces)
                    self.prompt = RED + self.user + " ! " + RESET
                    self.super = True
                else:
                    print("need a passcode to become a "+RED+"super"+RESET+" user")

            elif words[0] == 'normal':
                self.prompt = self.user + " > "
                self.super = False
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
                        print(item[1] + ": " + item[4] + ", damage: [{}-{}]".format(item[2],item[3]))
                else: # inspect any item in the room
                    if len(words) > 1:
                        self.c.execute("SELECT * FROM item WHERE room_id='{}'".format(self.current_room))
                        items = self.c.fetchall()
                        if items is not None:
                            for item in items:
                                if item[1] == words[1]:
                                    print(item[1] + ": " + item[3] + ", damage: " + str(item[2]))
                continue

            elif words[0] == 'attack':
                self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
                mob = self.c.fetchone()
                if randrange(200) < 180: # todo: more player/mob stats
                    if mob[2] <= self.attack:
                        self.c.execute("DELETE FROM mobs WHERE room_id={}".format(self.current_room))
                        print("You killed {}!".format(mob[1]))
                        print("It dropped a {}".format(mob[3]))
                        self.place(mob[3])
                    else:
                        damage = mob[2] - self.attack
                        self.c.execute("UPDATE mobs SET health={} WHERE room_id={}".format(damage,self.current_room))
                        self.db.commit()
                        print("You did {} damage to {}. {} has {} health left".format(self.attack, mob[1], mob[1],mob[2]-self.attack))
                else:
                    print("{} dodged your attack!!".format(mob[1]))

            elif words[0] == 'list':
                self.c.execute('SELECT * FROM user')
                super = lambda y,x: RED + x + RESET if bool(y) else x
                online = lambda y: GREEN + y + RESET if 'online' in y else y
                print("name     | hp    | room | status  |" if self.super else "name     | status  |")
                for i in self.c.fetchall():
                    if self.super:
                        print(super(i[4],'{0: <8}'.format(i[0])) + " | " + color(i[2])+ '{0: <5}'.format(i[2]) + RESET + " | " + '{0: <4}'.format(i[3]) + " | " + online('{0: <7}'.format(i[5])) + " |") # fix formatting here for names
                    else:
                        print(super(i[4],'{0: <8}'.format(i[0]))+ " | " + online('{0: <7}'.format(i[5])) + " |") # fix formatting here for names

            elif words[0] == 'steal':
                chance = randrange(100)
                if chance > 80:  # todo: implement proper defense / offense stats
                    self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
                    mob = self.c.fetchone()
                    print("You stole a {} from the ".format(mob[3],mob[1]))
                    self.place(mob[3])
                else:
                    print("The {} caught you!".format(mob[1]))

            elif words[0] == 'stats':
                print("You have " + color(self.health) + str(self.health) + RESET + " health")
                print("Your attack is " + color(self.attack) + str(self.attack) + RESET)
                #print("You have {} equiped".format(self.equiped))
                continue

            elif words[0] == 'items':
                for i, item in enumerate(self.items):
                    self.c.execute('SELECT * from item WHERE name="{}" and owner="{}"'.format(item,self.user))
                    x = self.c.fetchone()
                    print(str(i+1) + " " + x[1] +": "+ x[3] + ", damage: " + str(x[2]))
                continue

            elif words[0] == 'take':
                self.c.execute('SELECT * FROM item WHERE room_id={}'.format(self.current_room))
                item = self.c.fetchall()
                if len(words) < 2:
                    print("usage: take <name>")
                    continue
                if item != []:
                    for x in item:
                        if words[1] == x[1]:
                            self.items.append(x[1])
                            if x[2] > self.attack:
                                self.attack = x[2]
                                print("Your attack is now {}".format(self.attack))
                            self.c.execute('UPDATE item SET owner="{}" WHERE room_id={}'.format(self.user,self.current_room))
                            self.c.execute('UPDATE item SET room_id=-1 WHERE owner="{}"'.format(self.user))
                            self.db.commit()
                            break

            elif words[0] == 'help':
                print( RED + "new, dig, normal, place, spawn, loot, vanish, tele" + RESET + " super, look, go, inspect, attack, steal, stats, items, take, help")
                continue

            else:
                print("unknown command {}".format(words[0]))
                continue

            self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
            mob = self.c.fetchone() # todo: have multiple mobs at once
            if not self.super and mob is not None:
                self.c.execute('SELECT damage FROM item WHERE name = "{}" AND owner="{}"'.format(mob[3],mob[1]))
                damage = self.c.fetchone()
                print(mob[1] + " attacked you! You lost " + str(damage[0])+ " health")
                self.health -= damage[0]
            self.db.commit()

    # helper function to place an item in current room
    def place(self,name,owner=""):
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
        # todo: change the schema so we mark rooms as we visit them,
        # and show the florid description only the first time we visit
        # a room, or if someone types "look" explicitly (so will
        # probably want a force_florid optional parameter to this function)
        self.c.execute("SELECT short_desc FROM rooms WHERE id={}".format(self.current_room))
        print(self.c.fetchone()[0])
        self.c.execute("SELECT florid_desc FROM rooms WHERE id={}".format(self.current_room))
        print(self.c.fetchone()[0])
        self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
        mob = self.c.fetchone()
        if mob:
            print("There is an " + mob[1] + " with " + str(mob[2]) + " health, carrying a " + mob[3])
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
        self.c.execute('INSERT INTO user (username, password, health, room_id, super, status) VALUES ("{}","{}",{},{},{},"{}")'.format(self.user,b64encode(psw.encode("utf-8")),self.health,1,int(self.super),"online"))
        self.db.commit()

    def authenticate(self):
        psw = input("password: ")
        self.c.execute('SELECT * FROM user WHERE username="{}" AND password="{}"'.format(self.user,b64encode(psw.encode("utf-8"))))
        correct = self.c.fetchone()
        if correct is None or len(correct) < 4:
            print("Incorrect password for user")
            self.login()
            return None
        if correct[4] == 1:
            self.prompt =  RED + self.user + " ! "+RESET
            self.super = True
        else:
            self.prompt = self.user + ' > '
            self.super = False
        self.current_room = correct[3]
        self.health = correct[2]  # base player health
        self.items = []  # base player inventory
        self.attack = 5 # base attack
        self.c.execute('SELECT name FROM item WHERE owner = "{}"'.format(self.user))
        for item in self.c.fetchall():
            self.items.append(item[0])
            self.c.execute('SELECT damage FROM item WHERE name="{}" AND owner="{}"'.format(item[0],self.user))
            damage = self.c.fetchone()
            if damage is not None:
                self.attack = max(self.attack,damage[0]) # updates attack value to best item
        self.c.execute('UPDATE user SET status="online" WHERE username="{}"'.format(self.user))
        self.db.commit()

    def saveuser(self):
        self.c.execute('UPDATE user SET health={}, super={}, room_id={}, status="offline" WHERE username="{}"'.format(self.health,int(self.super),self.current_room,self.user)) # isn't working rn
        self.db.commit()
        print("Saved")
        self.db.close()

    # handle startup
    def CreateDatabase(self):
        self.c.execute("CREATE TABLE rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, short_desc TEXT, florid_desc TEXT)")
        self.c.execute("CREATE TABLE mobs (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, health INTEGER, loot TEXT, room_id INTEGER)")
        self.c.execute("CREATE TABLE loot (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, min INTEGER, max INTEGER, desc TEXT)") # items have range of damage
        self.c.execute("CREATE TABLE item (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, damage INTEGER, desc TEXT, room_id INTEGER, owner TEXT)") # specific items have damage value
        self.c.execute("CREATE TABLE exits (from_room INTEGER, to_room INTEGER, dir TEXT)")
        self.c.execute("CREATE TABLE user (username TEXT, password TEXT, health INTEGER, room_id INTEGER, super INTEGER, status TEXT)")
        self.c.execute("INSERT INTO rooms (florid_desc, short_desc) VALUES ('You are standing at the entrance of what appears to be a vast, complex cave.', 'entrance')")
        self.db.commit()

    def super_com(self, words):
        if words[0] == 'dig':
            # Only super users can create new rooms
            line = " ".join(words)
            descs = line.split("|")
            words = descs[0].split()
            if len(words) < 3 or len(descs) != 3:
                print("usage: dig <direction> <reverse> | <name> | <description>")
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
                print("usage: place <loot>")
            self.place(words[1])

        elif words[0] == 'tele':
            if len(words) < 2:
                print("usage: tele <room_id>")
                return
            self.c.execute('SELECT id FROM rooms')
            x = [row[0] for row in self.c.fetchall()]
            if int(words[1]) in x:
                self.current_room = int(words[1])
                print(BLUE + "You teleported!" + RESET)
                self.doLook()
            else:
                print("Not a valid id")
                return

        elif words[0] == 'map':
            self.c.execute('SELECT * FROM rooms')
            x = self.c.fetchall()
            print("id| Description | Long Description | Users? | Loot")
            for i in x:
                print("{} | {} | {}".format(i[0], i[1], i[2]))

        elif words[0] == 'vanish':
            query = "DELETE FROM mobs WHERE room_id={}".format(self.current_room) # deletes all mobs in current room
            self.c.execute(query)

        elif words[0] == 'spawn':
            if len(words) < 4:
                print("usage: spawn <name> <health> <loot>")
                return
            self.c.execute('SELECT * FROM loot WHERE name = "{}"'.format(words[3]))
            loot = self.c.fetchall()
            if (loot is None):
                print("that isn't valid loot, try adding it with \'loot {}...\'".format(words[3]))
                return
            loot = loot[0]
            damage = randrange(loot[2],loot[3])
            query = 'INSERT INTO mobs (desc, health, loot, room_id) VALUES ("{}", {}, "{}", {})'.format(words[1].strip(), int(damage), words[3], self.current_room)
            self.c.execute(query)
            self.c.execute('INSERT INTO item (name, damage, desc, room_id, owner) VALUES ("{}",{},"{}",{},"{}")'.format(loot[1],damage, loot[4], -1, words[1]))
            self.db.commit()

        elif words[0] == 'loot':
            if len(words) < 4:
                print("usage: loot <name> <min> <max> | <description of item> OR loot list")
                return
            line = " ".join(words)
            descs = line.split("|")
            words = descs[0].split()
            query = 'INSERT INTO loot (name, min, max, desc) VALUES ("{}", {}, {}, "{}")'.format(words[1].strip(), int(words[2]), int(words[3]), descs[1].strip())
            self.c.execute(query)
            self.db.commit()

        elif words[0] == "table":
            if len(words) < 2:
                print("usage: table <type>")
                return
            try:
                self.c.execute("SELECT * FROM {}".format(words[1]))
                x = self.c.fetchall()
            except:
                print(RED + "not a valid table" + RESET)
                return
            for i in x:
                for j in i:
                    print("{} | ".format(j),end='')
                print("")

        elif words[0] == "debug":
            x = input("Enter passcode: ") # just to make it a little harder to make a big error
            if b64encode(x.encode("utf-8")) == b'Tm9vb28=':
                line = " ".join(words)
                descs = line.split("|")
                if "SELECT" not in descs[1]:
                    print(RED + "only SELECT is allowed" + RESET)
                    return
                try:
                    self.c.execute(descs[1])
                    print(self.c.fetchall())
                except:
                    print(RED + "bad command" + RESET)
            else:
                print(RED + "bad passcode " + RESET)

assert sys.version_info >= (3,0), "This program requires Python 3"

histfile = ".shell-history"

if __name__ == '__main__':
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        open(histfile, 'wb').close()

    d = Dungeon()
    d.db = sqlite3.connect("dungeon.map")
    d.c = d.db.cursor()
    d.login()
    print("Welcome to the dungeon. Try 'look' 'go' and 'dig'")
    d.repl()
