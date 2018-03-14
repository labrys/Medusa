<%
    import logging

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    log.debug('Loading inc_quality_chooser')
%>
<%!
    import logging
    from medusa import app
    from medusa.common import Quality, qualityPresets, qualityPresetStrings

    log = logging.getLogger(__name__)
    log.addHandler(logging.NullHandler())

    try:
        __quality = int(show.quality)
    except NameError:
        __quality = int(app.QUALITY_DEFAULT)

    log.debug(__quality)

    allowed_qualities, preferred_qualities = Quality.split_quality(__quality)
    overall_quality = Quality.combine_qualities(allowed_qualities, preferred_qualities)
    log.debug(allowed_qualities)
    log.debug(preferred_qualities)
    log.debug(overall_quality)
    selected = None
%>
<select id="qualityPreset" name="quality_preset" class="form-control form-control-inline input-sm">
    <option value="0">Custom</option>
    % for curPreset in qualityPresets:
        <option value="${curPreset}" ${'selected="selected"' if curPreset == overall_quality else ''} ${('', 'style="padding-left: 15px;"')[qualityPresetStrings[curPreset].endswith("0p")]}>${qualityPresetStrings[curPreset]}</option>
    % endfor
</select>
<div id="customQualityWrapper">
    <div id="customQuality" style="padding-left: 0;">
        <p><b><strong>Preferred</strong></b> qualities will replace those in <b><strong>allowed</strong></b>, even if they are lower.</p>
        <div style="padding-right: 40px; text-align: left; float: left;">
            <h5>Allowed</h5>
            <% any_quality_list = [x for x in Quality.qualityStrings if x > Quality.NONE] %>
            <select id="allowed_qualities" name="allowed_qualities" multiple="multiple" size="${len(any_quality_list)}" class="form-control form-control-inline input-sm">
            % for cur_quality in sorted(any_quality_list):
                <option value="${cur_quality}" ${'selected="selected"' if cur_quality in allowed_qualities else ''}>${Quality.qualityStrings[cur_quality]}</option>
            % endfor
            </select>
        </div>
        <div style="text-align: left; float: left;">
            <h5>Preferred</h5>
            <% preferred_quality_list =  [x for x in Quality.qualityStrings if x >= Quality.SDTV and x < Quality.UNKNOWN] %>
            <select id="preferred_qualities" name="preferred_qualities" multiple="multiple" size="${len(preferred_quality_list)}" class="form-control form-control-inline input-sm">
            % for cur_quality in sorted(preferred_quality_list):
                <option value="${cur_quality}" ${'selected="selected"' if cur_quality in preferred_qualities else ''}>${Quality.qualityStrings[cur_quality]}</option>
            % endfor
            </select>
        </div>
    </div>
    <div id="qualityExplanation">
        <h5><b>Quality setting explanation:</b></h5>
        <h5 id="allowedText">This will download <b>any</b> of these qualities and then stops searching: <label id="allowedExplanation">${', '.join([Quality.qualityStrings[i] for i in allowed_qualities])}</label></h5>
        <h5 id="preferredText1">Downloads <b>any</b> of these qualities: <label id="allowedPreferredExplanation">${', '.join([Quality.qualityStrings[i] for i in allowed_qualities + preferred_qualities])}</label></h5>
        <h5 id="preferredText2">But it will stop searching when one of these is downloaded:  <label id="preferredExplanation">${', '.join([Quality.qualityStrings[i] for i in preferred_qualities])}</label></h5>
    </div>
    <div>
        <h5 class="red-text" id="backloggedEpisodes"></h5>
    </div>
    <div id="archive" style="display: none;">
        <h5>
            <b>
                Archive downloaded episodes that are not currently in <a target="_blank" href="manage/backlogOverview/"><font color="blue"><u>backlog</u>.</font></a>
            </b>
                <br />Avoids unnecessarily increasing your backlog
            </br>
        </h5>
        <input class="btn btn-inline" type="button" id="archiveEpisodes" value="Archive episodes" />
        <h5 id="archivedStatus"></h5>
    </div>
</div>
