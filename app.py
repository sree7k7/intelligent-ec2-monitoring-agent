#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infrastructure.infra_stack import AgentStack

app = cdk.App()
infra_stack = AgentStack(app, "AgentStack")

# alb = AlbStack(app, "AlbStack", vpc=basic_stack.vpc, instances=basic_stack.instances)


app.synth()