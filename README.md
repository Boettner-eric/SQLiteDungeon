SQLite Dungeon
==============
A project developed for Intro to Operating Systems

Features:
- Mobs and Loot assigned to rooms
- Random range for items
- Attack mechanics
- 17+ commands
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
- super * (will be added to authentication list later)
- Create loot items with custom damage and descriptions
- Spawn custom mobs with loot items
- Create new rooms and passages
- Delete mobs from rooms
- Teleport to any room by its id
- list all user profiles

On the way:
- User authentication using sql (done - but add encryption)
- Multiplayer support (chat, interactions, fights?)
- Better stats (defense, chance, magic...)
- Automatic random dungeon generation
- Fix bug when dropping up taking duplicate items (currently just does command for both)
- Many bug fixes

Enjoy!
