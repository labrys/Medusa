<%
    import logging

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading {}'.format(__file__))
%>
<%inherit file="/layouts/main.mako"/>
<%block name="content">
<h2>${subject}</h2>
${message}
</%block>
