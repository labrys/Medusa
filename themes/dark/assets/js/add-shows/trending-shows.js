MEDUSA.add_series.trending_series = function() {
    // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
    $.updateBlackWhiteList(undefined);
    $('#trending_series').loadRemoteShows(
        'add_series/get_trending_series/?trakt_list=' + $('#trakt_list').val(),
        'Loading trending shows...',
        'Trakt timed out, refresh page to try again'
    );

    $('#traktlistselection').on('change', e => {
        const trakt_list = e.target.value;
        window.history.replaceState({}, document.title, 'add_series/trending_series/?trakt_list=' + trakt_list);
        // Update the jquery tab hrefs, when switching trakt list.
        $('#trakt-tab-1').attr('href', document.location.href.split('=')[0] + '=' + e.target.value);
        $('#trakt-tab-2').attr('href', document.location.href.split('=')[0] + '=' + e.target.value);
        $('#trending_series').loadRemoteShows(
            'add_series/get_trending_series/?trakt_list=' + trakt_list,
            'Loading trending shows...',
            'Trakt timed out, refresh page to try again'
        );
        $('h1.header').text('Trakt ' + $('option[value="' + e.target.value + '"]')[0].innerText);
    });

    $.initAddShowById();
    $.initBlackListShowById();
    $.root_dirCheck();
};
