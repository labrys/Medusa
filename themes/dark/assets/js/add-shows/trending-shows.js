MEDUSA.add_series.trendingShows = function() {
    // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
    $.updateBlackWhiteList(undefined);
    $('#trending_series').loadRemoteShows(
        'add_series/get_trending_series/?traktList=' + $('#traktList').val(),
        'Loading trending shows...',
        'Trakt timed out, refresh page to try again'
    );

    $('#traktlistselection').on('change', e => {
        const traktList = e.target.value;
        window.history.replaceState({}, document.title, 'add_series/trending_series/?traktList=' + traktList);
        // Update the jquery tab hrefs, when switching trakt list.
        $('#trakt-tab-1').attr('href', document.location.href.split('=')[0] + '=' + e.target.value);
        $('#trakt-tab-2').attr('href', document.location.href.split('=')[0] + '=' + e.target.value);
        $('#trending_series').loadRemoteShows(
            'add_series/get_trending_series/?traktList=' + traktList,
            'Loading trending shows...',
            'Trakt timed out, refresh page to try again'
        );
        $('h1.header').text('Trakt ' + $('option[value="' + e.target.value + '"]')[0].innerText);
    });

    $.initAddShowById();
    $.initBlackListShowById();
    $.rootDirCheck();
};
