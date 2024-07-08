import json

with open('/home/astalum/discordbot/konsei/discordbot-attend/reactions.json','r') as f:
    d_update = json.load(f)
    reactions=["Soprano_attend", "Soprano_absent", "Alto_attend", "Alto_absent", "Tenor_attend", "Tenor_absent", "Bass_attend", "Bass_absent", "Delay", "off_stage"]
    for name in reactions:
        d_update.setdefault(name)

with open('/home/astalum/discordbot/konsei/discordbot-attend/reactions.json','w') as f:
    json.dump(d_update, f, indent=4)