from dotenv import dotenv_values
from pymongo import MongoClient
from bson import ObjectId


def main() -> None:
    cfg = dotenv_values('.env')
    client = MongoClient(cfg['MONGO_URI'])
    db = client[cfg['MONGO_DB']]

    print('db', db.name)
    collections = sorted(db.list_collection_names())
    print('collections', collections)

    proj = db.projects.find_one({'name': 'Inventory Management System'})
    print('project_found', bool(proj))
    if not proj:
        return

    pid = proj['_id']
    pid_str = str(pid)
    try:
        pid_oid = ObjectId(pid_str)
    except Exception:
        pid_oid = None

    print('project_id', pid, 'type', type(pid).__name__)

    for coll_name in ['projects_member', 'projects_members', 'project_members', 'project_member']:
        if coll_name not in collections:
            continue
        coll = db[coll_name]
        print('\n--', coll_name)
        print('total', coll.count_documents({}))
        sample = coll.find_one({})
        print('sample_keys', sorted(sample.keys()) if sample else None)

        queries = [
            ('projectId==str', {'projectId': pid_str}),
            ('projectId==oid', {'projectId': pid}),
            ('projectId in [str,oid]', {'projectId': {'$in': [pid_str, pid]}}),
            ('project_id==str', {'project_id': pid_str}),
            ('project_id==oid', {'project_id': pid}),
        ]
        if pid_oid is not None:
            queries += [
                ('projectId==ObjectId(str)', {'projectId': pid_oid}),
                ('project_id==ObjectId(str)', {'project_id': pid_oid}),
                ('projectId in [str,ObjectId(str)]', {'projectId': {'$in': [pid_str, pid_oid]}}),
            ]

        for label, q in queries:
            try:
                c = coll.count_documents(q)
            except Exception as e:
                c = f'ERR {type(e).__name__}: {e}'
            print(label, c)

        docs = list(coll.find({'projectId': pid_str}, {'_id': 0}).limit(3))
        print('first_docs_projectId_str', docs)


if __name__ == '__main__':
    main()
