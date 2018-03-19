<%
    import logging

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading {}'.format(__file__))
%>
<%inherit file="/layouts/main.mako"/>
<%!
    from medusa import app
    from medusa.helpers import anon_url
    from medusa.indexers.api import IndexerAPI
%>
<%block name="scripts">
<script type="text/javascript" src="js/quality-chooser.js?${sbPID}"></script>
<script type="text/javascript" src="js/add-show-options.js?${sbPID}"></script>
<script type="text/javascript" src="js/blackwhite.js?${sbPID}"></script>
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
        <script>document.write('<ul><li><a href="' + document.location.href + '#core-component-group1">Add New Show</a></li></ul>')</script>
        <div id="core-component-group1" class="tab-pane active component-group">
            <div id="displayText"></div>
            <br>
            <form id="addShowForm" method="post" action="add_series/add_new_series" accept-charset="utf-8">
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Find a show on selected indexer(s)</legend>
                    <div class="stepDiv">
                        <input type="hidden" id="indexer_timeout" value="${app.INDEXER_TIMEOUT}" />
                        % if use_provided_info:
                            Show retrieved from existing metadata: <a href="${anon_url(IndexerAPI(provided_indexer).config['show_url'], provided_indexer_id)}">${provided_indexer_name}</a>
                            <input type="hidden" id="indexer_lang" name="indexer_lang" value="en" />
                            <input type="hidden" id="which_series" name="which_series" value="${provided_indexer_id}" />
                            <input type="hidden" id="provided_indexer" name="provided_indexer" value="${provided_indexer}" />
                            <input type="hidden" id="providedName" value="${provided_indexer_name}" />
                        % else:
                            <input type="text" id="nameToSearch" value="${default_show_name}" class="form-control form-control-inline input-sm input350"/>
                            &nbsp;&nbsp;
                            <select name="indexer_lang" id="indexerLangSelect" class="form-control form-control-inline input-sm bfh-languages" data-blank="false" data-language="${app.INDEXER_DEFAULT_LANGUAGE}" data-available="${','.join(IndexerAPI().config['valid_languages'])}">
                            </select><b>*</b>
                            &nbsp;
                            <select name="provided_indexer" id="provided_indexer" class="form-control form-control-inline input-sm">
                                <option value="0" ${'' if provided_indexer else 'selected="selected"'}>All Indexers</option>
                                % for indexer in indexers:
                                    <option value="${indexer}" ${'selected="selected"' if provided_indexer == indexer else ''}>
                                        ${indexers[indexer]}
                                    </option>
                                % endfor
                            </select>
                            &nbsp;
                            <input class="btn btn-inline" type="button" id="searchName" value="Search" />
                            <br><br>
                            <b>*</b> This will only affect the language of the retrieved metadata file contents and episode filenames.<br>
                            This <b>DOES NOT</b> allow Medusa to download non-english TV episodes!<br><br>
                            <div id="searchResults" style="height: 100%;"><br></div>
                        % endif
                    </div>
                </fieldset>
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Pick the parent folder</legend>
                    <div class="stepDiv">
                        % if provided_show_dir:
                            Pre-chosen Destination Folder: <b>${provided_show_dir}</b> <br>
                            <input type="hidden" id="full_series_path" name="full_series_path" value="${provided_show_dir}" /><br>
                        % else:
                            <%include file="/inc_root_dirs.mako"/>
                        % endif
                    </div>
                </fieldset>
                <fieldset class="sectionwrap">
                    <legend class="legendStep">Customize options</legend>
                    <div class="stepDiv">
                        <%include file="/inc_add_series_options.mako"/>
                    </div>
                </fieldset>
                % for curNextDir in other_shows:
                <input type="hidden" name="other_shows" value="${curNextDir}" />
                % endfor
                <input type="hidden" name="skip_series" id="skip_series" value="" />
            </form>
            <br>
            <div style="width: 100%; text-align: center;">
                <input class="btn" type="button" id="addShowButton" value="Add Show" disabled="disabled" />
                % if provided_show_dir:
                <input class="btn" type="button" id="skip_seriesButton" value="Skip Show" />
                % endif
            </div>
        </div>
    </div>
</div>
</%block>