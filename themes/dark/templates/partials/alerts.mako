<%!
    import logging

    from medusa import app

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading alerts')
%>
<!-- BEGIN ALERTS -->
% if app.BRANCH and app.BRANCH != 'master' and not app.DEVELOPER and loggedIn:
<div class="text-center">
<div class="alert alert-danger upgrade-notification hidden-print" role="alert">
    <span>You're using the ${app.BRANCH} branch. Please use 'master' unless specifically asked</span>
</div>
</div>
% endif
% if app.NEWEST_VERSION_STRING and loggedIn:
<div class="text-center">
<div class="alert alert-success upgrade-notification hidden-print" role="alert">
    <span>${app.NEWEST_VERSION_STRING}</span>
</div>
</div>
% endif
<!-- END ALERTS -->
