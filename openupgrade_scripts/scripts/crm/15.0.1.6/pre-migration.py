import re

from lxml import etree
from openupgradelib import openupgrade


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


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.convert_field_to_html(env.cr, "crm_lead", "description", "description")
    openupgrade.logged_query(
        env.cr,
        """
        ALTER TABLE crm_team_member
        ADD COLUMN assignment_max INTEGER DEFAULT 30;
        ALTER TABLE crm_team_member ALTER COLUMN assignment_max DROP DEFAULT;
        """,
    )
    _rename_field_on_dashboard(
        env, "crm.lead", "activity_date_deadline_my", "my_activity_date_deadline"
    )
