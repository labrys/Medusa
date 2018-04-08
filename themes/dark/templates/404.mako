<%
    import logging

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading {}'.format(__file__))
%>
<%inherit file="/layouts/main.mako"/>
<%block name="content">
<h1 class="header">${header}</h1>
<div class="align-center">
You have reached this page by accident, please check the url.
</div>
</%block>
