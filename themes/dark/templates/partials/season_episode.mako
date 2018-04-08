<%
    import logging

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading season_episode')
%>
Manual search for:<br>
    <a href="home/display_series?indexername=${show.indexer_name}&seriesid=${show.series_id}" class="snatchTitle">${show.name}</a> / Season ${season}
        % if manual_search_type != 'season':
            Episode ${episode}
        % endif
    </a>
