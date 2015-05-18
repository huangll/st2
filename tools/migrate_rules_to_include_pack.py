#!/usr/bin/env python
# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mongoengine as me
from oslo.config import cfg

from st2common import config
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.models.db.reactor import ActionExecutionSpecDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.base import Access, ContentPackResource


class Migration(object):
    class RuleDB(stormbase.StormFoundationDB, stormbase.TagsMixin,
                 stormbase.ContentPackResourceMixin):
        """Specifies the action to invoke on the occurrence of a Trigger. It
        also includes the transformation to perform to match the impedance
        between the payload of a TriggerInstance and input of a action.
        Attribute:
            trigger: Trigger that trips this rule.
            criteria:
            action: Action to execute when the rule is tripped.
            status: enabled or disabled. If disabled occurrence of the trigger
            does not lead to execution of a action and vice-versa.
        """
        name = me.StringField(required=True)
        ref = me.StringField(required=True)
        description = me.StringField()
        pack = me.StringField(
            required=False,
            help_text='Name of the content pack.',
            unique_with='name')
        trigger = me.StringField()
        criteria = stormbase.EscapedDictField()
        action = me.EmbeddedDocumentField(ActionExecutionSpecDB)
        enabled = me.BooleanField(required=True, default=True,
                                  help_text=u'Flag indicating whether the rule is enabled.')

        meta = {
            'indexes': stormbase.TagsMixin.get_indices()
        }

# specialized access objects
rule_access_with_pack = MongoDBAccess(Migration.RuleDB)


class RuleDB(stormbase.StormBaseDB, stormbase.TagsMixin):
    """Specifies the action to invoke on the occurrence of a Trigger. It
    also includes the transformation to perform to match the impedance
    between the payload of a TriggerInstance and input of a action.
    Attribute:
        trigger: Trigger that trips this rule.
        criteria:
        action: Action to execute when the rule is tripped.
        status: enabled or disabled. If disabled occurrence of the trigger
        does not lead to execution of a action and vice-versa.
    """
    trigger = me.StringField()
    criteria = stormbase.EscapedDictField()
    action = me.EmbeddedDocumentField(ActionExecutionSpecDB)
    enabled = me.BooleanField(required=True, default=True,
                              help_text=u'Flag indicating whether the rule is enabled.')

    meta = {
        'indexes': stormbase.TagsMixin.get_indices()
    }

rule_access_without_pack = MongoDBAccess(RuleDB)


class RuleWithoutPack(Access):
    impl = rule_access_without_pack

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, object):
        # For Rule name is unique.
        name = getattr(object, 'name', '')
        return cls.get_by_name(name)


class RuleWithPack(ContentPackResource):
    impl = rule_access_with_pack

    @classmethod
    def _get_impl(cls):
        return cls.impl


def migrate_rules():
    existing_rules = RuleWithoutPack.get_all()

    for rule in existing_rules:
        rule_with_pack = Migration.RuleDB(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            trigger=rule.trigger,
            criteria=rule.criteria,
            action=rule.action,
            enabled=rule.enabled,
            pack=DEFAULT_PACK_NAME,
            ref=ResourceReference.to_string_reference(pack=DEFAULT_PACK_NAME,
                                                      name=rule.name)
        )
        print('Migrating rule: %s to rule: %s' % (rule.name, rule_with_pack.ref))
        RuleWithPack.add_or_update(rule_with_pack)


def main():
    config.parse_args()

    # Connect to db.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)

    # Migrate rules.
    migrate_rules()

    # Disconnect from db.
    db_teardown()


if __name__ == '__main__':
    main()
