import sys
sys.path.insert(0, '.')
from app.core.database import SessionLocal
from app.models.campaign import Campaign
import json

db = SessionLocal()
c = db.query(Campaign).order_by(Campaign.created_at.desc()).first()
if c and c.result_json:
    data = json.loads(c.result_json)
    print(f"Top keys: {list(data.keys())}")
    print(f"Status: {data.get('status')}")
    print(f"Exceptions: {data.get('exceptions', [])}")
    print()
    for a in data.get('activityRuns', []):
        if a.get('kind') == 'step':
            step_id = a.get('stepId', '?')
            output_str = a.get('outputs', {}).get('output', '')
            if output_str:
                try:
                    step_data = json.loads(output_str)
                    print(f"Step: {step_id}")
                    print(f"  Keys: {list(step_data.keys())}")
                    if 'publish_results' in step_data:
                        print(f"  publish_results: {json.dumps(step_data['publish_results'], indent=2)[:500]}")
                    if 'published' in step_data:
                        print(f"  published: {json.dumps(step_data['published'], indent=2)[:500]}")
                    if 'topic' in step_data:
                        print(f"  topic: {step_data['topic']}")
                    if 'exceptions' in step_data:
                        print(f"  exceptions: {json.dumps(step_data['exceptions'], indent=2)[:500]}")
                    print()
                except json.JSONDecodeError:
                    print(f"Step: {step_id} -> raw: {output_str[:100]}")
db.close()
