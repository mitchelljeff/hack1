from flask import Flask, jsonify, abort, request
import tensorflow as tf


from jack.core.data_structures import jtr_to_qasetting
from jack.readers import readers,  reader_from_file



app = Flask(__name__)


et2rels={}
rel2qf={}

with open("en-r2q.format") as f:
    for line in f:
        fields=line.rstrip("\n").split("\t")
        rel=fields[0]
        e1type=rel[0:3]
        qformat=fields[1]
        if e1type not in et2rels:
            et2rels[e1type]=[]
        et2rels[e1type].append(rel)
        rel2qf[rel]=qformat



reader = reader_from_file("remqa_reader")

@app.route('/api/qa', methods=['POST'])
def get_relations():
    if not request.json:
        abort(400)
    support="NoAnswerFound "+request.json["text"]
    entities=request.json["nel"]["entities"]
    qas=[]
    entdict={}
    mentions={}
    for e in entities:
        entity=e["entity"]
        ementions=e["mentions"]
        eid=entity["id"]
        entdict[eid]=entity
        mentions[eid]=ementions
        e1type=entity["type"].lower()
        name=entity["currlangForm"]
        rels=et2rels[e1type]
        for rel in rels:
            qid=eid+"\t"+rel
            question=rel2qf[rel].format(name)
            qas.append({"question":{"text":question,"id":qid},"answers":[{"text":"","span":[0,0]}]})
    instances=[{"questions":qas,"support":[{"text":support}]}]      
    data ={'meta':'SUMMA','instances':instances}
    qa = jtr_to_qasetting(data)
    answers = reader.process_dataset(qa, 1)
    results=[]
    for i, a in enumerate(answers):
        if a.text != "NoAnswerFound" and a.score > 0.0:
            eid, rel = qa[i][0].id.split("\t")
            ent = entdict[eid]
            source = mentions[eid][0]["souceDocument"]["id"]
            name = mentions[eid][0]["text"]
            arg0 = [{"entities":{eid:name},"name":name}]
            arg1 = [{"text":a.text}]
            roles = {"ARG0":arg0, "ARG1":arg1}
            fact = {"entities":{eid:ent}, "source":source, "name":rel, "roles":roles, "score":str(a.score)}
            
            results.append({"question":qa[i][0].question, "answer":a.text, "span":[int(a.span[0]),int(a.span[1])], "score":str(a.score)})
    return jsonify(results)



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
