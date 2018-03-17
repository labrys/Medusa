// @TODO: Remove this when we fully drop support for IE > 8
// Avoid `console` errors in browsers that lack a console.
(function() { // eslint-disable-line wrap-iife
    let method;
    const noop = function noop() {}; // eslint-disable-line func-names
    const methods = [
        'assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error',
        'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log',
        'markTimeline', 'profile', 'profileEnd', 'table', 'time', 'timeEnd',
        'timeStamp', 'trace', 'warn'
    ];
    let length = methods.length;
    window.console = window.console || {};
    const console = window.console;

    while (length--) {
        method = methods[length];

        // Only stub undefined methods.
        if (!console[method]) {
            console[method] = noop;
        }
    }
}());

$(document).ready(() => {
    function setDefault(which, force) {
        if (which !== undefined && which.length === 0) {
            return;
        }

        if ($('#whichDefaultRootDir').val() === which && force !== true) {
            return;
        }

        // Put an asterisk on the text
        if ($('#' + which).text().charAt(0) !== '*') {
            $('#' + which).text('*' + $('#' + which).text());
        }

        // If there's an existing one then take the asterisk off
        if ($('#whichDefaultRootDir').val() && force !== true) {
            const oldDefault = $('#' + $('#whichDefaultRootDir').val());
            oldDefault.text(oldDefault.text().substring(1));
        }

        $('#whichDefaultRootDir').val(which);
    }

    function syncOptionIDs() {
        // Re-sync option ids
        let i = 0;
        $('#root_dirs option').each(function() {
            $(this).prop('id', 'rd-' + (i++));
        });
    }

    function refreshRootDirs() {
        if ($('#root_dirs').length === 0) {
            /* Trigger change event as $.root_dirCheck() function is not
               always available when this section of code is called. */
            $('#root_dirs').trigger('change');
            return;
        }

        let doDisable = 'true';

        // Re-sync option ids
        syncOptionIDs();

        // If nothing's selected then select the default
        if ($('#root_dirs option:selected').length === 0 && $('#whichDefaultRootDir').val().length !== 0) {
            $('#' + $('#whichDefaultRootDir').val()).prop('selected', true);
        }

        // If something's selected then we have some behavior to figure out
        if ($('#root_dirs option:selected').length !== 0) {
            doDisable = '';
        }

        // Update the elements
        $('#deleteRootDir').prop('disabled', doDisable);
        $('#defaultRootDir').prop('disabled', doDisable);
        $('#editRootDir').prop('disabled', doDisable);

        let dirString = '';
        if ($('#whichDefaultRootDir').val().length >= 4) {
            dirString = $('#whichDefaultRootDir').val().substr(3);
        }
        $('#root_dirs option').each(function() {
            if (dirString.length !== 0) {
                dirString += '|' + $(this).val();
            }
        });

        $('#root_dirText').val(dirString);
        // Manually trigger change event as setting .val directly doesn't
        $('#root_dirs').trigger('change');
    }

    function addRootDir(path) {
        if (path.length === 0) {
            return;
        }

        // Check if it's the first one
        let isDefault = false;
        if ($('#whichDefaultRootDir').val().length === 0) {
            isDefault = true;
        }

        $('#root_dirs').append('<option value="' + path + '">' + path + '</option>');

        syncOptionIDs();

        if (isDefault) {
            setDefault($('#root_dirs option').attr('id'));
        }

        refreshRootDirs();
        $.get('config/general/save_root_dirs', {
            root_dirString: $('#root_dirText').val()
        });
    }

    function editRootDir(path) {
        if (path.length === 0) {
            return;
        }

        // As long as something is selected
        if ($('#root_dirs option:selected').length !== 0) {
            // Update the selected one with the provided path
            if ($('#root_dirs option:selected').attr('id') === $('#whichDefaultRootDir').val()) {
                $('#root_dirs option:selected').text('*' + path);
            } else {
                $('#root_dirs option:selected').text(path);
            }
            $('#root_dirs option:selected').val(path);
        }

        refreshRootDirs();
        $.get('config/general/save_root_dirs', {
            root_dirString: $('#root_dirText').val()
        });
    }

    $('#addRootDir').on('click', function() {
        $(this).nFileBrowser(addRootDir);
    });
    $('#editRootDir').on('click', function() {
        $(this).nFileBrowser(editRootDir, {
            initialDir: $('#root_dirs option:selected').val()
        });
    });

    $('#deleteRootDir').on('click', () => {
        if ($('#root_dirs option:selected').length !== 0) {
            const to_delete = $('#root_dirs option:selected');
            const newDefault = (to_delete.attr('id') === $('#whichDefaultRootDir').val());
            const deletedNum = $('#root_dirs option:selected').attr('id').substr(3);

            to_delete.remove();
            syncOptionIDs();

            if (newDefault) {
                console.log('new default when deleting');

                // We deleted the default so this isn't valid anymore
                $('#whichDefaultRootDir').val('');

                // If we're deleting the default and there are options left then pick a new default
                if ($('#root_dirs option').length !== 0) {
                    setDefault($('#root_dirs option').attr('id'));
                }
            } else if ($('#whichDefaultRootDir').val().length !== 0) {
                const oldDefaultNum = $('#whichDefaultRootDir').val().substr(3);
                if (oldDefaultNum > deletedNum) {
                    $('#whichDefaultRootDir').val('rd-' + (oldDefaultNum - 1));
                }
            }
        }
        refreshRootDirs();
        $.get('config/general/save_root_dirs', {
            root_dirString: $('#root_dirText').val()
        });
    });

    $('#defaultRootDir').on('click', () => {
        if ($('#root_dirs option:selected').length !== 0) {
            setDefault($('#root_dirs option:selected').attr('id'));
        }
        refreshRootDirs();
        $.get('config/general/save_root_dirs', {
            root_dirString: $('#root_dirText').val()
        });
    });
    $('#root_dirs').click(refreshRootDirs);

    // Set up buttons on page load
    syncOptionIDs();
    setDefault($('#whichDefaultRootDir').val(), true);
    refreshRootDirs();
});
