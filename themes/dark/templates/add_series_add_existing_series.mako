<%
    import logging

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading {}'.format(__file__))
%>
<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
%>
<%block name="scripts">
<script type="text/javascript" src="js/quality-chooser.js?${sbPID}"></script>
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
</%block>
<%block name="content">
% if not header is UNDEFINED:
    <h1 class="header">${header}</h1>
% else:
    <h1 class="title">${title}</h1>
% endif
<div id="new_seriesPortal">
    <div id="config-components">
        ## @TODO: Fix this stupid hack
        <script>document.write('<ul><li><a href="' + document.location.href + '#core-component-group1">Add Existing Show</a></li></ul>')</script>
        <div id="core-component-group1" class="tab-pane active component-group">
            <form id="addShowForm" method="post" action="add_series/addExistingShows" accept-charset="utf-8">
                <div id="tabs">
                    <ul>
                        <li><a href="${base_url}add_series/existing_series/#tabs-1">Manage Directories</a></li>
                        <li><a href="${base_url}add_series/existing_series/#tabs-2">Customize Options</a></li>
                    </ul>
                    <div id="tabs-1" class="existingtabs">
                        <%include file="/inc_root_dirs.mako"/>
                    </div>
                    <div id="tabs-2" class="existingtabs">
                        <%include file="/inc_add_series_options.mako"/>
                    </div>
                </div>
                <br>
                <p>Medusa can add existing shows, using the current options, by using locally stored NFO/XML metadata to eliminate user interaction.
                If you would rather have Medusa prompt you to customize each show, then use the checkbox below.</p>
                <p><input type="checkbox" name="promptForSettings" id="promptForSettings" /> <label for="promptForSettings">Prompt me to set settings for each show</label></p>
                <hr>
                <p><b>Displaying folders within these directories which aren't already added to Medusa:</b></p>
                <ul id="root_dirStaticList"><li></li></ul>
                <br>
                <div id="tableDiv"></div>
                <br>
                <br>
                <input class="btn" type="button" value="Submit" id="submitShowDirs" />
            </form>
        </div>
    </div>
</div>
</%block>
