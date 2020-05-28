function D = pintraj2vid(exp,sn,sess,block,wrist,hand,task,trial)

pause(5);

base_dir = 'data';
exp_dir  = exp;
hand_dir = fullfile(base_dir,exp_dir,sn,sess,wrist,hand);
MOV = csvread(fullfile(hand_dir,block,[sn '_' sess '_' hand '_' task '_' trial '.csv']));

%subtract by baseline
time = MOV(end,1) - MOV(1,1);
force = MOV(:,3:17).*9.8; % convert to Newtons
baseline = median(force(1:100,:));
normf = bsxfun(@minus, force, baseline);

log_file = [sn '_' sess '_' hand '_log.yml'];
L = ReadYaml(fullfile(hand_dir,log_file));
% offset for finger locations specific to individual hand
r(1)   = 5-str2num(L.Thumb.DEVICEMountLength);
r(2)   = 5-str2num(L.Index.DEVICEMountLength);
r(3)   = 5-str2num(L.Middle.DEVICEMountLength);
r(4)   = 5-str2num(L.Ring.DEVICEMountLength);
r(5)   = 5-str2num(L.Pinky.DEVICEMountLength);
ang(1) = str2num(L.Thumb.DEVICEMountAngle);
ang(2) = str2num(L.Index.DEVICEMountAngle);
ang(3) = str2num(L.Middle.DEVICEMountAngle);
ang(4) = str2num(L.Ring.DEVICEMountAngle);
ang(5) = str2num(L.Pinky.DEVICEMountAngle);
fcenter = zeros(5,3);
for f=1:5
    fcenter(f,1) = r(f)*cosd(180+ang(f)); % x
    fcenter(f,2) = r(f)*sind(180+ang(f)); % y
end
if strcmp(hand,'Left')
    fcenter = flip(fcenter); % flip finger order
end
% offset hardcoded for display (as show in the experiment)

fcenter(1,1) = fcenter(1,1)-5;
fcenter(1,2) = fcenter(1,2)+3;
fcenter(2,1) = fcenter(2,1)-2.5;
fcenter(2,2) = fcenter(2,2)+4.5;
fcenter(3,1) = fcenter(3,1)-0; % treat middle finger as the center
fcenter(3,2) = fcenter(3,2)+5;
fcenter(4,1) = fcenter(4,1)+2.5;
fcenter(4,2) = fcenter(4,2)+4.5;
fcenter(5,1) = fcenter(5,1)+5;
fcenter(5,2) = fcenter(5,2)+3;
fcenter = fcenter./10.*9.8; % convert to Newtons

% load target file
T = readtable(fullfile(hand_dir,block,'final_targets.csv'));
tcenter = [0,0,0];
for f=1:5
    idx = f;
    if strcmp(hand,'Left')
        idx = 6-f;
    end
    if ismember(f,str2num(T.fings{str2num(trial)}))
        tcenter = tcenter + fcenter(idx,:);
    end
end

A = T{str2num(trial),12:14}./10.*9.8; % target offset
if strcmp(hand,'Left')
    A(1) = -A(1);
end
tcenter = tcenter./length(strsplit(T.fings{str2num(trial)}));

%v = VideoWriter('pin_dom.avi');
%v.FrameRate = 20;
%datperframe = round(length(MOV)/time/v.FrameRate);
FrameRate = 60;
datperframe = round(length(MOV)/time/FrameRate);
%%v.FrameRate = length(MOV)/time;
%open(v)

color = [0,0,0;0,0,0;0,0,0;0,0,0;0,0,0];
traj = [];
linelim = [-5 5];
lim = [-5 5];
for i = 1:datperframe:length(MOV)
    scatter3(normf(i,1:3:end)+fcenter(:,1)',normf(i,2:3:end)+fcenter(:,2)',normf(i,3:3:end)+fcenter(:,3)',...
        [20 20 20 20 20],color,'filled');
    hold on
    scatter3(tcenter(1)+A(1), tcenter(2)+A(2), tcenter(3)+A(3),40,[.5,0.5,0.5],'filled')
    traj = [traj; normf(i,1:3:end)+fcenter(:,1)',normf(i,2:3:end)+fcenter(:,2)',normf(i,3:3:end)+fcenter(:,3)'];
    if i > 1
        plot3(traj(:,1:5),traj(:,6:10),traj(:,11:15))
    end
    xlabel('X'); ylabel('Y'); zlabel('Z');
    line(lim, [0,0], [0,0],'Color', 'k');
    line([0,0], lim, [0 0],'Color', 'k');
    line([0,0], [0,0], lim,'Color', 'k');
    
    set(gca,'XLim',lim,'YLim',lim,'ZLim',lim);
    line(linelim, [0,0], [0,0],'Color', 'k');
    line([0,0], linelim, [0 0],'Color', 'k');
    line([0,0], [0,0], linelim,'Color', 'k');
    %set(gca,'visible','off');
    frame = getframe(gcf);
    
    %writeVideo(v,frame);
    hold off
end
%close(v)
end