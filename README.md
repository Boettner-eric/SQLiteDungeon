SQLite Dungeon
==============
A project developed for Intro to Operating Systems

Features:
- Mobs and Loot assigned to rooms
- Random range for items
- Attack mechanics
- Tons of commands
- Super user for creation of dungeon with mobs and loot
- User profiles
- Clocked and nonclocked commands

Setup:
```
p3 dungeon.py < setup.txt > /dev/null
```
- Modify setup.txt to change layout of a generated map
- Use super user to make changes to an existing map

Super User:
- super *
- Create loot items with custom damage and descriptions
- Spawn custom mobs with loot items
- Create new rooms and passages
- Delete mobs from rooms
- Teleport to any room by its id
- list all user profiles
- show map of full dungeon

On the way:
- User authentication using sql (done - but add better encryption)
- Multiplayer support (chat, interactions, fights?)
- Better stats (defense, chance, magic...)
- Automatic random dungeon generation
- Many bug fixes

Enjoy!
