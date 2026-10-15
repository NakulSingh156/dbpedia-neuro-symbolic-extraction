"""Stage 1 first-pass labels (Claude, GUIDELINES v1.1) for sample_300.jsonl -> labels_sample_300.json.

Keyed by sample position (1-based). Unlisted positions = no unnamed reference.
Tuple forms: (type, span) or (type, span, {flags}).
"""
import json

TP, TD, TZ = "T-PRON", "T-DEF", "T-ZERO"
L = {
  3:[(TD,"The team")], 6:[(TP,"Its")], 10:[(TP,"She")], 11:[(TD,"the location")], 12:[(TD,"The song")],
  14:[(TP,"It")],
  17:[(TD,"the party's"), ("O-DESC","the 1993 election",{"kb_entity":"likely"})],
  18:[(TP,"She")], 25:[(TZ,"(wingspan)")],
  26:[(TP,"His"), ("O-REL","His brother",{"relation":"sibling","named_elsewhere":"no","plural":"no","kb_entity":"likely"}),
      ("O-REL","two nephews",{"relation":"nephew","named_elsewhere":"no","plural":"yes","kb_entity":"likely"})],
  27:[(TP,"it")], 28:[(TP,"its")], 29:[(TZ,"(heats of the event)")], 34:[(TD,"the area")], 35:[(TD,"The newspaper")],
  36:[(TP,"It")], 37:[(TD,"The neighobourhood")], 38:[(TZ,"(housing in the neighbourhood)")], 39:[(TP,"He")],
  42:[(TZ,"(the school's programs)")], 46:[(TZ,"(population)")], 56:[(TD,"The village")], 57:[(TP,"it")],
  59:[("O-REL","the management and staff of the former South Africa Arts Council Opera",{"relation":"staff of","named_elsewhere":"no","plural":"yes","kb_entity":"unlikely"})],
  60:[(TP,"He")],
  61:[(TP,"His"), ("O-REL","His namesake nephew",{"relation":"nephew","named_elsewhere":"no","plural":"no","kb_entity":"likely","note":"'namesake' gives the name (Carlo Zucchi, architect) indirectly"})],
  62:[(TP,"he")], 63:[(TD,"The series")], 64:[(TP,"It")], 69:[(TP,"Its")], 71:[(TZ,"(wingspan)")],
  72:[(TD,"The method")], 75:[(TZ,"(leaves)")],
  82:[(TP,"He")], 83:[(TD,"The episode")], 85:[(TP,"his")], 88:[(TZ,"(mascot)")], 90:[(TD,"the community")],
  95:[(TZ,"(larvae)")], 96:[(TP,"It")], 97:[(TP,"He")], 99:[(TP,"He")], 101:[(TP,"She")], 104:[(TP,"He")],
  105:[(TP,"he")], 110:[(TP,"He")],
  111:[(TP,"he"), ("O-REL","eight children",{"relation":"child","named_elsewhere":"no","plural":"yes","kb_entity":"unlikely"})],
  112:[(TD,"Both properties",{"note":"topic plus Oakenwald Terrace, named in the previous sentence"})],
  113:[(TP,"his")],
  114:[("O-REL","The English adaptation",{"relation":"adaptation of","named_elsewhere":"no","plural":"no","kb_entity":"unlikely"})],
  117:[(TP,"him")],
  118:[(TP,"He"), ("O-DESC","the region",{"kb_entity":"likely","note":"implicit anchor: the topic's home region"})],
  122:[(TP,"She")], 125:[(TP,"He")], 127:[(TP,"His")],
  128:[(TP,"He"), ("O-DESC","the Peruvian squad that won the Copa América 1975",{"kb_entity":"likely"})],
  129:[(TP,"It")],
  131:[(TP,"she"), ("O-REL","his cabinet",{"relation":"cabinet of","named_elsewhere":"no","plural":"no","kb_entity":"unlikely"})],
  133:[(TP,"its")], 134:[(TP,"It")],
  135:[(TP,"It"), ("O-DESC","a teenage girl",{"kb_entity":"unlikely","note":"fictional"}), ("O-DESC","a man",{"kb_entity":"unlikely","note":"fictional"})],
  140:[(TP,"he")], 141:[(TP,"He")], 142:[(TP,"It")], 143:[(TP,"He")], 147:[(TP,"He")], 151:[(TD,"the series")],
  153:[("O-DESC","the war",{"kb_entity":"likely","note":"Second Sino-Japanese War"})],
  160:[(TP,"It")], 161:[(TP,"It"), (TD,"the show")], 163:[(TP,"It")], 164:[(TD,"the temple")],
  170:[("O-DESC","the coveted title",{"kb_entity":"likely","named_elsewhere":"yes"})],
  171:[(TP,"He")],
  175:[("O-DESC","the shadow cabinet",{"kb_entity":"likely"})],
  176:[(TP,"It")],
  177:[("O-REL","The third season",{"relation":"season of (topic, implicit)","named_elsewhere":"no","plural":"no","kb_entity":"likely"})],
  178:[(TP,"It")], 184:[(TD,"the company")], 186:[(TZ,"(population)")], 187:[(TZ,"(demonym)")],
  190:[("O-DESC","the suspects",{"kb_entity":"unlikely","plural":"yes"})],
  191:[("O-REL","The present building",{"relation":"building of (topic, implicit)","named_elsewhere":"no","plural":"no","kb_entity":"unlikely"})],
  193:[(TZ,"(named by ANCA)")], 194:[(TP,"It")], 198:[(TP,"He")], 202:[(TP,"It")], 203:[(TP,"Its")], 204:[(TP,"It")],
  205:[(TP,"It")], 209:[(TZ,"(adults)")], 211:[(TP,"It")],
  212:[(TP,"His",{"note":"'His brother' is named in apposition in the same sentence -> excluded"})],
  215:[(TP,"It")], 216:[(TP,"It")], 219:[(TP,"It")], 223:[(TD,"The grant")], 225:[(TP,"it")], 233:[(TD,"The church")],
  234:[(TP,"Her")], 236:[(TP,"He")], 240:[(TD,"The school")], 241:[(TZ,"(name)")], 242:[(TZ,"(name)")], 243:[(TP,"its")],
  246:[("O-PRON","he",{"note":"fictional protagonist"}), ("O-DESC","two young girls",{"kb_entity":"unlikely","plural":"yes","note":"fictional"})],
  247:[(TD,"the line")], 249:[(TP,"It")], 250:[(TP,"It")], 253:[(TP,"He")], 260:[(TD,"The town")], 265:[(TP,"It")],
  266:[(TP,"It")], 267:[("O-PRON","It",{"note":"Benedum-Trees Building, named in the previous sentence"})], 268:[(TZ,"(named by)")], 272:[(TP,"He")], 275:[(TP,"It"), (TD,"the city")],
  276:[(TD,"the song")], 277:[(TZ,"(train services)")], 279:[(TD,"the campus")], 282:[(TZ,"(specimen)")],
  286:[(TD,"The station")], 289:[(TP,"It")], 290:[(TD,"The waltz")], 291:[(TD,"The station")], 292:[(TP,"It")],
  294:[(TP,"He")], 296:[(TP,"He")], 298:[(TZ,"(winners)")], 299:[(TP,"it")],
}

S = [json.loads(l) for l in open("sample_300.jsonl")]
out = []
for i, s in enumerate(S, 1):
    labs = []
    for t in L.get(i, []):
        d = {"type": t[0], "span": t[1]}
        if len(t) > 2: d.update(t[2])
        labs.append(d)
    out.append({"pos": i, "id": s["id"], "labels": labs})
json.dump({"annotator": "claude-first-pass", "guidelines": "v1.1", "items": out}, open("labels_sample_300.json", "w"), indent=1, ensure_ascii=False)
print("wrote", len(out))
