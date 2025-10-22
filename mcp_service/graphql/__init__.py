#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GraphQL API模块。"""

from .schema import schema, create_graphql_app

__all__ = [
    'schema',
    'create_graphql_app',
]
