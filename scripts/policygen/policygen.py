import argparse
import json
import os
from typing import Any, List, Dict

from collections import OrderedDict

from pydantic import BaseModel, Field
import jinja2
import yaml


class Source(BaseModel):
    kind: str
    config: Dict[str, Any] = Field(default_factory=dict)


class Config(BaseModel):
    sources: List[Source]


def generate(config: Config):
    searchpath = os.path.join(os.path.dirname(__file__), "sources")
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=searchpath))

    def represent_ordereddict(dumper, data):
        return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

    yaml.add_representer(OrderedDict, represent_ordereddict)

    policy: Any = OrderedDict(version="1", sources=[])

    for sourceconf in config.sources:
        template = env.get_template(f"{sourceconf.kind}/template.yml")
        source_template_yaml = template.render(config=sourceconf.config)
        source_template = yaml.safe_load(source_template_yaml)
        policy['sources'].append(source_template['source'])

    return yaml.dump(policy, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str,
                        default='policygen.config.json',
                        help='Config file name')
    parser.add_argument('--output', type=str, help='Output file name')
    parser.add_argument('--print', action='store_true', help='Print to console')
    args = parser.parse_args()

    with open(args.config, "r") as f:
        raw_config = json.loads(f.read())
    config = Config(**raw_config)

    output = generate(config)

    if args.print:
        print(output)
    else:
        if not os.path.exists('.guardette'):
            os.makedirs('.guardette')
        with open(".guardette/policy.yml", 'w') as f:
            f.write(output)
