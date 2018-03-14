MEDUSA.add_series.recommended_series = function() {
    // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
    $.updateBlackWhiteList(undefined);
    $('#recommended_series').loadRemoteShows(
        'add_series/getrecommended_series/',
        'Loading recommended shows...',
        'Trakt timed out, refresh page to try again'
    );

    $.initAddShowById();
    $.initBlackListShowById();
    $.initRemoteShowGrid();
    $.root_dirCheck();
};
