% Plot data of all 5 fingers to visualize trajectory during grasp task.
function plot_trajectory(subj,session,wrist,hand,block)

trajectory_dir = fullfile('data','exp_2',subj,session,wrist,hand);
colors = colormap(lines);
tasks = readtable(fullfile(trajectory_dir,block,'final_targets.csv'));
files = dir(fullfile(trajectory_dir,block,[subj '_' session '_' hand '*.csv']));
subj_info = dir(fullfile('data','exp_1',[subj '_' session '_' hand '_log.yml']));

for i=1:4
    pos_end = [];
    finger_pos = [];
    positions = [];
    tcenter = [0,0,0];
    highlighted_indices = str2num(char(tasks{i,'fings'}));
    for f=1:5
        D = csvread(fullfile(trajectory_dir,block,files(i).name));
        D = D(:,((f-1)*3+3:(f-1)*3+5)); % grab xyz columns for each finger
        baseline = mean(D(1:100,:));
        D = (D - repmat(baseline,length(D),1)).*1000; % centering data for each trial 
        figure(i);
        if f==1
            p1= plot3(D(:,1)-1000,D(:,2)-1200,D(:,3));
            centre = [-1000,-1200,0];
        elseif f==2
            p2=plot3(D(:,1)-600,D(:,2)-400,D(:,3));
            centre = [-600,-400,0];
        elseif f==3
            p3=plot3(D(:,1),D(:,2),D(:,3));
            centre = [0,0,0];
        elseif f==4
            p4=plot3(D(:,1)+600,D(:,2)-300,D(:,3));
            centre = [600,-300,0];
        elseif f==5
            p5=plot3(D(:,1)+1000,D(:,2)-800,D(:,3));
            centre = [1000,-800,0];
            legend([p1,p2,p3,p4,p5],'Thumb','Index','Middle','Ring','Pinky');
        end
        hold on; grid on;
        scatter3(centre(1),centre(2),centre(3),100,'k','filled');
        axis_lim = [-1500 1500];
        xlabel('X'); ylabel('Y'); zlabel('Z');
        line(axis_lim, [0,0], [0,0],'Color', 'k');
        line([0,0], axis_lim, [0,0],'Color', 'k');
        line([0,0], [0,0], axis_lim,'Color', 'k');
        
        if ismember(f,highlighted_indices)
            tcenter = tcenter + centre;
        end
    end
    A = tasks{i,12:14}.*100;
    tcenter = tcenter / length(highlighted_indices);
    scatter3(tcenter(1)+A(1), tcenter(2)+A(2), tcenter(3)+A(3));
    
    title([string(tasks{i,'dirtext'}),'-T',files(i).name(end-4:end-4)],'fontsize',14);
end
