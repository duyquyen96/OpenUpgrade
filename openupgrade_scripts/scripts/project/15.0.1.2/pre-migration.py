import re

from lxml import etree
from openupgradelib import openupgrade

_column_renames = {
    "project_task": [
        ("user_id", None),
    ],
}


def _rename_field_on_filters(cr, model, old_field, new_field):
    # Example of replaced domain: [['field', '=', self], ...]
    # TODO: Rename when the field is part of a submodel (ex. m2one.field)
    cr.execute(
        """
        UPDATE ir_filters
        SET domain = regexp_replace(domain, %(old_pattern)s, %(new_pattern)s, 'g')
        WHERE model_id = %%s
            AND domain ~ %(old_pattern)s
        """
        % {
            "old_pattern": r"""$$('|")%s('|")$$""" % old_field,
            "new_pattern": r"$$\1%s\2$$" % new_field,
        },
        (model,),
    )
    # Examples of replaced contexts:
    # {'group_by': ['field', 'other_field'], 'other_key':value}
    # {'group_by': ['date_field:month']}
    # {'other_key': value, 'group_by': ['other_field', 'field']}
    # {'group_by': ['other_field'],'col_group_by': ['field']}
    cr.execute(
        r"""
        UPDATE ir_filters
        SET context = regexp_replace(
            context, %(old_pattern)s, %(new_pattern)s, 'g'
        )
        WHERE model_id = %%s
            AND context ~ %(old_pattern)s
        """
        % {
            "old_pattern": (
                r"""$$('group_by'|'col_group_by'|'graph_groupbys'
                       |'pivot_measures'|'pivot_row_groupby'|'pivot_column_groupby'
                    ):([\s*][^\]]*)"""
                r"'%s(:day|:week|:month|:year){0,1}'(.*?\])$$"
            )
            % old_field,
            "new_pattern": r"$$\1:\2'%s\3'\4$$" % new_field,
        },
        (model,),
    )
    # Examples of replaced contexts:
    # {'graph_measure': 'field'
    cr.execute(
        r"""
        UPDATE ir_filters
        SET context = regexp_replace(
            context, %(old_pattern)s, %(new_pattern)s, 'g'
        )
        WHERE model_id = %%s
            AND context ~ %(old_pattern)s
        """
        % {
            "old_pattern": (
                r"$$'graph_measure':([\s*])'%s(:day|:week|:month|:year){0,1}'$$"
            )
            % old_field,
            "new_pattern": r"$$'graph_measure':\1'%s\2'$$" % new_field,
        },
        (model,),
    )


def _rename_field_on_dashboard(env, model, old_field, new_field):
    dashboard_view_data = env["ir.ui.view.custom"].search([])
    for r in dashboard_view_data:
        parsed_arch = etree.XML(r.arch)
        act_window_ids = parsed_arch.xpath("//action/@name")
        actions = env["ir.actions.act_window"].search(
            [
                ("id", "in", act_window_ids),
                ("res_model", "=", model),
            ]
        )
        for action in actions:
            condition_for_element = "//action[@name='{}']".format(action.id)
            condition_for_domain = "//action[@name='{}']/@domain".format(action.id)
            condition_for_context = "//action[@name='{}']/@context".format(action.id)
            arch_element = parsed_arch.xpath(condition_for_element)
            for index in range(len(arch_element)):
                arch_domain = arch_element[index].xpath(condition_for_domain)[index]
                arch_context = arch_element[index].xpath(condition_for_context)[index]

                arch_context = re.sub(
                    r"""('group_by'|'col_group_by'|'graph_groupbys'
                        |'pivot_measures'|'pivot_row_groupby'|'pivot_column_groupby'
                        ):([\s*][^\]]*)'%s(:day|:week|:month|:year){0,1}'(.*?\])"""
                    % old_field,
                    r"\1:\2'%s\3'\4" % new_field,
                    arch_context,
                )

                arch_context = re.sub(
                    r"""'graph_measure':([\s*])'%s(:day|:week|:month|:year){0,1}'"""
                    % old_field,
                    r"'graph_measure':\1'%s\2'" % new_field,
                    arch_context,
                )

                arch_domain = re.sub(
                    r"""('|")%s('|")""" % old_field,
                    r"\1%s\2" % new_field,
                    arch_domain,
                )

                arch_element[index].set("domain", arch_domain)
                arch_element[index].set("context", arch_context)

            new_arch = etree.tostring(parsed_arch, encoding="unicode")

            r.write({"arch": new_arch})


def fill_project_project_allow_task_dependencies(env):
    openupgrade.add_fields(
        env,
        [
            (
                "allow_task_dependencies",
                "project.project",
                "project_project",
                "boolean",
                "bool",
                "project",
                True,
            ),
        ],
    )


def fill_project_project_last_update_status(env):
    openupgrade.add_fields(
        env,
        [
            (
                "last_update_status",
                "project.project",
                "project_project",
                "selection",
                "varchar",
                "project",
                "on_track",
            ),
        ],
    )


def adapt_project_task_dependency(env):
    # check if project_task_dependency was installed
    if not openupgrade.table_exists(env.cr, "project_task_dependency_task_rel"):
        return
    openupgrade.rename_tables(
        env.cr, [("project_task_dependency_task_rel", "task_dependencies_rel")]
    )
    openupgrade.rename_fields(
        env,
        [
            ("project.task", "project_task", "dependency_task_ids", "depend_on_ids"),
            ("project.task", "project_task", "depending_task_ids", "dependent_ids"),
        ],
    )
    openupgrade.rename_columns(
        env.cr, {"task_dependencies_rel": [("dependency_task_id", "depends_on_id")]}
    )


def rename_project_milestone_target_date(env):
    """If project_milestone is installed then rename column target_date
    to deadline.
    """
    if openupgrade.column_exists(env.cr, "project_milestone", "target_date"):
        openupgrade.rename_columns(
            env.cr,
            {"project_milestone": [("target_date", "deadline")]},
        )


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_columns(env.cr, _column_renames)
    adapt_project_task_dependency(env)
    fill_project_project_allow_task_dependencies(env)
    fill_project_project_last_update_status(env)
    rename_project_milestone_target_date(env)
    _rename_field_on_filters(env.cr, "project.task", "user_id", "user_ids")
    _rename_field_on_dashboard(env, "project.task", "user_id", "user_ids")
