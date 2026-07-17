import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

import jinja2
import yaml
from pydantic import BaseModel, Field


class Source(BaseModel):
    kind: str
    config: dict[str, Any] = Field(default_factory=dict)


class Config(BaseModel):
    sources: list[Source]


def generate(config: Config):
    searchpath = Path(__file__).parent / "sources"
    # YAML output is not HTML; autoescaping would change policy values.
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=searchpath), autoescape=False)  # noqa: S701

    def represent_ordereddict(dumper, data):
        return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())

    yaml.add_representer(OrderedDict, represent_ordereddict)

    policy: Any = OrderedDict(version="1", sources=[])

    for sourceconf in config.sources:
        template = env.get_template(f"{sourceconf.kind}/template.yml")
        source_template_yaml = template.render(config=sourceconf.config)
        source_template = yaml.safe_load(source_template_yaml)
        policy["sources"].append(source_template["source"])

    return yaml.dump(policy, sort_keys=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="policygen.config.json", help="Config file name")
    parser.add_argument("--output", type=str, help="Output file name")
    parser.add_argument("--print", action="store_true", help="Print to console")
    args = parser.parse_args()

    raw_config = json.loads(Path(args.config).read_text())
    config = Config(**raw_config)

    output = generate(config)

    if args.print:
        print(output)
    else:
        output_dir = Path(".guardette")
        output_dir.mkdir(exist_ok=True)
        (output_dir / "policy.yml").write_text(output)
