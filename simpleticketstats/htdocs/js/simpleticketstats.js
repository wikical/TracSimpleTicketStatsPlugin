$(document).ready(function() {
    $('.simpleticketstats').each(function( index ) {
        var id = $( this ).attr('id');
        var width = window[id+'_width'];
        var height = window[id+'_height'];
        var closedTickets = window[id+'_closedTickets'];
        var openedTickets = window[id+'_openedTickets'];
        var reopenedTickets = window[id+'_reopenedTickets'];
        var openTickets = window[id+'_openTickets'];
        var graph = $( this ).width(width).height(height),
        barSettings = { show: true, barWidth: 86400000 };
        $.plot($( this ),
        [
            {
                data: closedTickets,
                label: 'Closed',
                bars: barSettings,
                color: 3
            },
            {
                data: openedTickets,
                label: 'New',
                bars: barSettings,
                color: 2
            },
            {
                data: reopenedTickets,
                label: 'Reopened',
                bars: barSettings,
                color: 1
            },
            {
                data: openTickets,
                label: 'Open',
                yaxis: 2,
                lines: { show: true },
                color: 0
            }
        ],
        {
            xaxis: { mode: 'time', minTickSize: [1, "day"] },
            yaxis: { min: 0, label: 'Tickets' },
            y2axis: { min: 0 },
            legend: { position: 'nw' }
        });
    });
});
