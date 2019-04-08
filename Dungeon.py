import sys
import sqlite3
import readline
from random import randrange

GREEN = '\033[32m'
RED = '\033[91m'
BLUE = '\033[34m'
YELLOW = '\033[33m'
PURPLE = '\033[95m'
RESET = '\033[0m'


def color(num):
    if num > 50:
        return GREEN
    if num > 25:
        return YELLOW
    return RED


class Dungeon:
    """
    """

    dungeon_map = "dungeon.map"
    prompt = '> '
    attack = 5  # base attack "punch"
    health = 100  # base player health
    items = []  # base player inventory
    user = input("username: ")
    # password = input("password: ")
    # todo: authenticate users with table of passwords

    """
    Note:
    - Commands with "continue" don't progress clock/attack schedule
    - super user has elevated permissions to modify the world but can't interact/fight mobs
    """
    def repl(self):
        self.db = sqlite3.connect(self.dungeon_map)
        self.c = self.db.cursor()
        self.current_room = self.getEntranceOrCreateDatabase()
        self.super = False

        self.doLook()
        self.c.execute('SELECT name FROM inventory WHERE player = "{}"'.format(self.user))
        for item in self.c.fetchall():
            self.items.append(item[0])
            self.c.execute('SELECT damage FROM loot WHERE name="{}"'.format(item[0]))
            damage = self.c.fetchone()
            self.attack = max(self.attack,damage[0]) # updates attack value to best item

        while True:
            if self.health <= 0:
                print(RED+"you died..."+RESET)
                print("you seemed to have lost your items and ended up back at the begining of the Dungeon")
                self.current_room = self.getEntranceOrCreateDatabase()
                self.health = 100
                self.items = []

            line = input(self.prompt)
            words = line.split()

            if len(words) == 0:
                continue
            elif words[0] in ('exit', 'quit', 'q'):
                break

            # destroy the dungeon and start over
            # maybe we should ask "are you sure?"
            elif words[0] in ('new'):
                if not super:
                    print("must be super user to do that try: \'super\'")
                    continue
                self.c.execute("DROP TABLE rooms")
                self.current_room = self.getEntranceOrCreateDatabase()

            elif words[0] == 'look':
                self.doLook()

            elif words[0] == 'go':
                # move to an adjacent room.
                # todo - allow someone to type the direction of an
                # adjacent room without "go"
                if len(words) < 2:
                    print("usage: go <direction>")
                    continue
                self.c.execute("SELECT to_room FROM exits WHERE from_room = {} AND dir='{}'".format(self.current_room, words[1]))
                new_room_p = self.c.fetchone()
                if new_room_p is None:
                    print("You can't go that way")
                    continue
                else:
                    self.current_room = new_room_p[0]
                    self.doLook()

            elif words[0] == 'dig':
                # Only super users can create new rooms
                if not self.super:
                    print("must be super user to do that try: \'super\'")
                    continue
                descs = line.split("|")
                words = descs[0].split()
                if len(words) < 3 or len(descs) != 3:
                    print("usage: dig <direction> <reverse> | <brief description of new room> | <florid description of new room>")
                    continue
                forward = words[1]
                reverse = words[2]
                brief = descs[1].strip() # strip removes whitespace around |'s
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

            elif words[0] == 'super':
                if len(words) != 1 and words[1] == '*': # add a password here (must be one string with no spaces)
                    self.prompt =  RED+"! "+RESET
                    self.super = True
                else:
                    print("need a passcode to become a "+RED+"super"+RESET+" user")

            elif words[0] == 'normal':
                self.prompt = "> "
                self.super = False

            elif words[0] == 'place':
                if not self.super:
                    print("must be super user to do that try: \'super\'")
                    continue
                if len(words) < 2:
                    print("usage: place <loot>")
                self.place(words[1])

            elif words[0] == 'tele':
                if not self.super:
                    print("must be super user to do that try: \'super\'")
                    continue
                self.c.execute('SELECT id FROM rooms')
                x = [row[0] for row in self.c.fetchall()]
                print(x)
                y = int(input("Pick room id to teleport to: "))
                if y in x:
                    self.current_room = y
                    print("You teleported!")
                    self.doLook()
                else:
                    print("Not a valid id")
                    continue

            elif words[0] == 'inspect':
                if self.super: # inspect any item
                    self.c.execute("SELECT name FROM loot".format(self.current_room))
                    for item in self.c.fetchall():
                        print("{}  ".format(item[0]), end='')
                    print("")
                    name = input("Pick an item to inspect: ")
                    self.c.execute("SELECT * FROM loot WHERE name='{}'".format(name))
                    item = self.c.fetchone()
                    if item is not None:
                        print(item[1] +": "+ item[3] + ", damage: " + str(item[2]))
                else: # inspect any item in the room
                    self.c.execute("SELECT * FROM item WHERE room_id='{}'".format(self.current_room))
                    item = self.c.fetchone()
                    if item is not None:
                        print(item[1] +": "+ item[3] + ", damage: " + str(item[2]))
                continue

            elif words[0] == 'vanish':
                if not self.super:
                    print("must be super user to do that try: \'super\'")
                    continue
                query = "DELETE FROM mobs WHERE room_id={}".format(self.current_room) # deletes all mobs in current room
                self.c.execute(query)

            elif words[0] == 'spawn':
                if not self.super:
                    print("must be super user to do that try: \'super\'")
                    continue
                if len(words) < 4:
                    print("usage: spawn <name> <health> <loot>")
                    continue
                self.c.execute('SELECT name FROM loot WHERE name = "{}"'.format(words[3]))
                if (self.c.fetchall() is None):
                    print("that isn't valid loot, try adding it with \'loot {}...\'".format(words[3]))
                    continue
                query = 'INSERT INTO mobs (desc, health, loot, room_id) VALUES ("{}", {}, "{}", {})'.format(words[1].strip(), int(words[2]), words[3], self.current_room)
                self.c.execute(query)

            elif words[0] == 'loot':
                if not self.super:
                    print("must be super user to do that try: \'super\'")
                    continue
                if len(words) < 3:
                    print("usage: loot <name> <damage> | <description of item> OR loot list")
                    continue
                descs = line.split("|")
                words = descs[0].split()
                query = 'INSERT INTO loot (name, damage, desc) VALUES ("{}", {}, "{}")'.format(words[1].strip(), int(words[2]), descs[1].strip())
                self.c.execute(query)

            elif words[0] == 'attack':
                if self.super:
                    print("must be normal user to do that try: \'normal\'")
                    continue
                self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
                mob = self.c.fetchone()
                if randrange(100) < 80: # todo: more player/mob stats
                    if mob[2] < self.attack:
                        self.c.execute("DELETE FROM mobs WHERE room_id={}".format(self.current_room))
                        print("You killed {}!".format(mob[1]))
                        print("It dropped a {}".format(mob[3]))
                        self.place(mob[3])
                    else:
                        damage = mob[2] - self.attack
                        self.c.execute("UPDATE mobs SET health={} WHERE room_id={}".format(damage,self.current_room))
                        print("You did {} damage to {}. {} has {} health left".format(self.attack, mob[1],mob[1],mob[2]-self.attack))
                else:
                    print("{} dodged your attack!!".format(mob[1]))

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
                continue

            elif words[0] == 'items':
                for i, item in enumerate(self.items):
                    print(str(i+1) + ". " + item)
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
                            self.c.execute('INSERT INTO inventory (player, name) VALUES ("{}","{}")'.format(self.user, x[1]))
                            self.c.execute('DELETE FROM item WHERE room_id={} AND name="{}"'.format(self.current_room, x[1]))
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
                self.c.execute('SELECT damage FROM loot WHERE name = "{}"'.format(mob[3]))
                damage = self.c.fetchone()[0]
                print(mob[1] + " attacked you! You lost " + str(damage)+ " health")
                self.health -= damage
            self.db.commit() # here?

        # all done, clean exit
        print("bye!")
        self.db.close()

    # helper function to place an item in current room
    def place(self,name):
        self.c.execute("SELECT * FROM loot WHERE name='{}'".format(name))
        item = self.c.fetchone()
        self.c.execute('INSERT INTO item (name, damage, desc, room_id) VALUES ("{}",{},"{}",{})'.format(name,item[2],item[3],self.current_room))
        pass

    # describe this room and its exits
    def doLook(self):
        # todo: change the schema so we mark rooms as we visit them,
        # and show the florid description only the first time we visit
        # a room, or if someone types "look" explicitly (so will
        # probably want a force_florid optional parameter to this function)
        self.c.execute("SELECT florid_desc FROM rooms WHERE id={}".format(self.current_room))
        print(self.c.fetchone()[0])
        self.c.execute("SELECT * FROM mobs WHERE room_id={}".format(self.current_room))
        mob = self.c.fetchone()
        if mob:
            print("There is an " + mob[1] + " with " + str(mob[2]) + " health, carrying a " + mob[3])
        else:
            print("There are no mobs in this room")
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

    def authenticate(self,username,password):
        print("Todo")

    # handle startup
    def getEntranceOrCreateDatabase(self):
        # check if we've initialized the database before
        # does it have a "rooms" table
        self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rooms'")
        db_exists = self.c.fetchone()
        if (db_exists is None):
            self.c.execute("DROP TABLE if exists rooms")
            self.c.execute("DROP TABLE if exists mobs")
            self.c.execute("DROP TABLE if exists loot")
            self.c.execute("DROP TABLE if exists exits")
            self.c.execute("DROP TABLE if exists inventory")
            self.c.execute("CREATE TABLE rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, short_desc TEXT, florid_desc TEXT)")
            self.c.execute("CREATE TABLE mobs (id INTEGER PRIMARY KEY AUTOINCREMENT, desc TEXT, health INTEGER, loot TEXT, room_id INTEGER)")
            self.c.execute("CREATE TABLE loot (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, damage INTEGER, desc TEXT)")
            self.c.execute("CREATE TABLE item (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, damage INTEGER, desc TEXT, room_id INTEGER)")
            self.c.execute("CREATE TABLE inventory (name TEXT, player TEXT)") ## add to all instances
            self.c.execute("CREATE TABLE exits (from_room INTEGER, to_room INTEGER, dir TEXT)")
            self.c.execute("INSERT INTO rooms (florid_desc, short_desc) VALUES ('You are standing at the entrance of what appears to be a vast, complex cave.', 'entrance')")
            self.db.commit()

        # now we know the db exists - fetch the first room, which is
        # the entrance
        self.c.execute("SELECT MIN(id) FROM rooms")
        entrance_p = self.c.fetchone()
        return entrance_p[0]

assert sys.version_info >= (3,0), "This program requires Python 3"

histfile = ".shell-history"

if __name__ == '__main__':
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        open(histfile, 'wb').close()

    d = Dungeon()
    print("Welcome to the dungeon. Try 'look' 'go' and 'dig'")
    d.repl()
